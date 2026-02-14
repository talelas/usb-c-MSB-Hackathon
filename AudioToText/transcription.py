"""
from faster_whisper import WhisperModel

# Choix du modèle : "tiny" ou "base" (très légers)
model_size = "base"

# Chargement du modèle (device="cpu" pour fonctionner sans GPU)
model = WhisperModel(model_size, device="cpu", compute_type="int8")

# Nom de votre fichier audio
audio_file = "test.mp3"  # Changez selon votre fichier

print(f"Transcription de {audio_file} en cours...")

# Transcription
segments, info = model.transcribe(audio_file, language="fr")

# Affichage du résultat
print("\n--- Résultat de la transcription ---\n")
for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")

# Sauvegarde dans un fichier texte
with open("transcription.txt", "w", encoding="utf-8") as f:
    for segment in segments:
        f.write(f"{segment.text}\n")

print("\n✅ Transcription sauvegardée dans 'transcription.txt'")
"""
from faster_whisper import WhisperModel

# Choix du modèle : "tiny" ou "base" (très légers)
model_size = "base"

# Chargement du modèle (device="cpu" pour fonctionner sans GPU)
model = WhisperModel(model_size, device="cpu", compute_type="int8")

# Nom de votre fichier audio
audio_file = "test.mp3"  # Changez selon votre fichier

print(f"Transcription de {audio_file} en cours...")

# Transcription EN ANGLAIS (changé de "fr" à "en")
segments, info = model.transcribe(audio_file, language="en")

# Affichage du résultat (SANS timestamps)
print("\n--- Résultat de la transcription ---\n")
full_text = ""
for segment in segments:
    print(segment.text)  # Affiche juste le texte
    full_text += segment.text + " "

# Sauvegarde dans un fichier texte (TEXTE BRUT SEULEMENT)
with open("transcription.txt", "w", encoding="utf-8") as f:
    f.write(full_text.strip())

print("\n✅ Transcription sauvegardée dans 'transcription.txt'")