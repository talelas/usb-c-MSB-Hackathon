"""
Event Queue Manager
Thread-safe queue for handling file events from multiple sources.
"""
import queue
import threading
import logging
from typing import Optional, Callable
from datetime import datetime

from .storage_schemas import FileEvent, EventType

logger = logging.getLogger(__name__)


def _enum_value(value) -> str:
    """Return enum value when present, otherwise string representation."""
    return getattr(value, "value", value)


class EventQueue:
    """
    Thread-safe queue for file events.
    Implements producer-consumer pattern for ingestion pipeline.
    """
    
    def __init__(self, maxsize: int = 1000):
        """
        Initialize event queue.
        
        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self.queue = queue.Queue(maxsize=maxsize)
        self.stats = {
            'total_events': 0,
            'events_processed': 0,
            'events_failed': 0,
            'event_types': {}
        }
        self._lock = threading.Lock()
        self._running = False
        self._workers = []
        
        logger.info(f"EventQueue initialized with maxsize={maxsize}")
    
    def put(self, event: FileEvent, block: bool = True, timeout: Optional[float] = None):
        """
        Add event to queue.
        
        Args:
            event: FileEvent to add
            block: Block if queue is full
            timeout: Timeout in seconds
        """
        try:
            self.queue.put(event, block=block, timeout=timeout)
            
            with self._lock:
                self.stats['total_events'] += 1
                event_type = _enum_value(event.event_type)
                self.stats['event_types'][event_type] = \
                    self.stats['event_types'].get(event_type, 0) + 1
            
            logger.debug(
                f"Event queued: {event.event_type} - {event.file_path} "
                f"(queue size: {self.queue.qsize()})"
            )
        
        except queue.Full:
            logger.warning(f"Queue full, dropping event: {event.file_path}")
            raise
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[FileEvent]:
        """
        Get event from queue.
        
        Args:
            block: Block if queue is empty
            timeout: Timeout in seconds
        
        Returns:
            FileEvent or None if timeout
        """
        try:
            event = self.queue.get(block=block, timeout=timeout)
            logger.debug(f"Event dequeued: {event.event_type} - {event.file_path}")
            return event
        
        except queue.Empty:
            return None
    
    def task_done(self):
        """Mark task as completed"""
        self.queue.task_done()
    
    def start_workers(self, processor: Callable, num_workers: int = 4):
        """
        Start consumer worker threads.
        
        Args:
            processor: Function to process events (takes FileEvent, returns bool)
            num_workers: Number of worker threads
        """
        if self._running:
            logger.warning("Workers already running")
            return
        
        self._running = True
        
        for i in range(num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(processor, i),
                daemon=True,
                name=f"EventWorker-{i}"
            )
            worker.start()
            self._workers.append(worker)
        
        logger.info(f"Started {num_workers} worker threads")
    
    def _worker_loop(self, processor: Callable, worker_id: int):
        """
        Worker thread loop.
        
        Args:
            processor: Event processing function
            worker_id: Worker identifier
        """
        logger.debug(f"Worker {worker_id} started")
        
        while self._running:
            try:
                # Get event with timeout to allow checking _running flag
                event = self.get(block=True, timeout=1.0)
                
                if event is None:
                    continue
                
                # Process event
                start_time = datetime.utcnow()
                success = False
                
                try:
                    success = processor(event)
                    processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    if success:
                        with self._lock:
                            self.stats['events_processed'] += 1
                        logger.debug(
                            f"Worker {worker_id} processed event in {processing_time:.2f}ms: "
                            f"{event.file_path}"
                        )
                    else:
                        with self._lock:
                            self.stats['events_failed'] += 1
                        logger.warning(
                            f"Worker {worker_id} failed to process: {event.file_path}"
                        )
                
                except Exception as e:
                    with self._lock:
                        self.stats['events_failed'] += 1
                    logger.error(
                        f"Worker {worker_id} error processing {event.file_path}: {e}",
                        exc_info=True
                    )
                
                finally:
                    self.task_done()
            
            except Exception as e:
                logger.error(f"Worker {worker_id} unexpected error: {e}", exc_info=True)
        
        logger.debug(f"Worker {worker_id} stopped")
    
    def stop_workers(self, wait: bool = True, timeout: float = 30.0):
        """
        Stop all worker threads.
        
        Args:
            wait: Wait for workers to finish
            timeout: Maximum wait time in seconds
        """
        if not self._running:
            return
        
        logger.info("Stopping workers...")
        self._running = False
        
        if wait and self._workers:
            # Wait for worker threads
            for worker in self._workers:
                worker.join(timeout=timeout / max(len(self._workers), 1))
                if worker.is_alive():
                    logger.warning(f"Worker {worker.name} did not stop in time")
        
        self._workers.clear()
        logger.info("All workers stopped")
    
    def size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self.queue.empty()
    
    def get_stats(self) -> dict:
        """Get queue statistics"""
        with self._lock:
            return {
                **self.stats,
                'queue_size': self.size(),
                'workers_running': len([w for w in self._workers if w.is_alive()])
            }


class EventDebouncer:
    """
    Debounces rapid file events.
    Useful for handling editors that create multiple write events.
    """
    
    def __init__(self, delay: float = 1.0):
        """
        Initialize debouncer.
        
        Args:
            delay: Debounce delay in seconds
        """
        self.delay = delay
        self._pending = {}  # file_path -> (event, timer)
        self._lock = threading.Lock()
    
    def debounce(self, event: FileEvent, callback: Callable):
        """
        Debounce event.
        
        Args:
            event: FileEvent to debounce
            callback: Function to call after delay
        """
        with self._lock:
            file_path = event.file_path
            
            # Cancel existing timer if any
            if file_path in self._pending:
                old_event, old_timer = self._pending[file_path]
                old_timer.cancel()
                logger.debug(f"Cancelled pending event for {file_path}")
            
            # Create new timer
            timer = threading.Timer(
                self.delay,
                self._fire_event,
                args=(file_path, event, callback)
            )
            timer.start()
            
            self._pending[file_path] = (event, timer)
            logger.debug(f"Debouncing event for {file_path} (delay: {self.delay}s)")
    
    def _fire_event(self, file_path: str, event: FileEvent, callback: Callable):
        """Fire debounced event"""
        with self._lock:
            if file_path in self._pending:
                del self._pending[file_path]
        
        logger.debug(f"Firing debounced event for {file_path}")
        callback(event)
    
    def cancel_all(self):
        """Cancel all pending events"""
        with self._lock:
            for file_path, (event, timer) in self._pending.items():
                timer.cancel()
            self._pending.clear()
        logger.info("Cancelled all pending debounced events")
