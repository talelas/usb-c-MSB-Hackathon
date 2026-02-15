import { getExtIcon } from "./theme";

// ─── MEDICAL DEMO: FILE SYSTEM TREE (for left sidebar) ─────────────
export const fileTree = [
  {
    id: "cat-pulmonary",
    name: "Chest X-Rays",
    type: "folder",
    ext: "folder",
    importance: 1.0,
    group: "pulmonary",
    children: [
      { id: "xray-0006", name: "IM-0006-0001.jpeg", type: "file", ext: "jpeg", importance: 0.8, group: "pulmonary", path: "/Chest X-Rays/IM-0006-0001.jpeg" },
      { id: "xray-0007", name: "IM-0007-0001.jpeg", type: "file", ext: "jpeg", importance: 0.8, group: "pulmonary", path: "/Chest X-Rays/IM-0007-0001.jpeg" },
      { id: "xray-0009", name: "IM-0009-0001.jpeg", type: "file", ext: "jpeg", importance: 0.75, group: "pulmonary", path: "/Chest X-Rays/IM-0009-0001.jpeg" },
      { id: "xray-0010", name: "IM-0010-0001.jpeg", type: "file", ext: "jpeg", importance: 0.75, group: "pulmonary", path: "/Chest X-Rays/IM-0010-0001.jpeg" },
    ],
  },
  {
    id: "cat-infectious",
    name: "Pneumonia Cases",
    type: "folder",
    ext: "folder",
    importance: 0.95,
    group: "infectious",
    children: [
      { id: "pneum-103", name: "person103_bacteria_490.jpeg", type: "file", ext: "jpeg", importance: 0.9, group: "infectious", path: "/Pneumonia Cases/person103_bacteria_490.jpeg" },
      { id: "pneum-104", name: "person104_bacteria_492.jpeg", type: "file", ext: "jpeg", importance: 0.85, group: "infectious", path: "/Pneumonia Cases/person104_bacteria_492.jpeg" },
      { id: "pneum-109a", name: "person109_bacteria_517.jpeg", type: "file", ext: "jpeg", importance: 0.85, group: "infectious", path: "/Pneumonia Cases/person109_bacteria_517.jpeg" },
      { id: "pneum-109b", name: "person109_bacteria_523.jpeg", type: "file", ext: "jpeg", importance: 0.8, group: "infectious", path: "/Pneumonia Cases/person109_bacteria_523.jpeg" },
    ],
  },
  {
    id: "cat-cardiac",
    name: "Heart Sounds",
    type: "folder",
    ext: "folder",
    importance: 0.9,
    group: "cardiac",
    children: [
      { id: "heart-1", name: "ElevenLabs_..01_37_16.mp3", type: "file", ext: "mp3", importance: 0.7, group: "cardiac", path: "/Heart Sounds/ElevenLabs_2026-02-15T01_37_16_Rachel.mp3" },
      { id: "heart-2", name: "ElevenLabs_..01_37_58.mp3", type: "file", ext: "mp3", importance: 0.7, group: "cardiac", path: "/Heart Sounds/ElevenLabs_2026-02-15T01_37_58_Rachel.mp3" },
      { id: "heart-3", name: "ElevenLabs_..01_38_38.mp3", type: "file", ext: "mp3", importance: 0.65, group: "cardiac", path: "/Heart Sounds/ElevenLabs_2026-02-15T01_38_38_Rachel.mp3" },
      { id: "heart-4", name: "ElevenLabs_..01_39_11.mp3", type: "file", ext: "mp3", importance: 0.65, group: "cardiac", path: "/Heart Sounds/ElevenLabs_2026-02-15T01_39_11_Rachel.mp3" },
      { id: "heart-5", name: "ElevenLabs_..01_39_35.mp3", type: "file", ext: "mp3", importance: 0.6, group: "cardiac", path: "/Heart Sounds/ElevenLabs_2026-02-15T01_39_35_Rachel.mp3" },
    ],
  },
  {
    id: "cat-surgical",
    name: "Surgical Records",
    type: "folder",
    ext: "folder",
    importance: 0.85,
    group: "surgical",
    children: [
      { id: "surg-593", name: "patient_593__Surgery.txt", type: "file", ext: "txt", importance: 0.9, group: "surgical", path: "/Surgical Records/patient_593__Surgery.txt" },
      { id: "surg-795", name: "patient_795__Surgery.txt", type: "file", ext: "txt", importance: 0.8, group: "surgical", path: "/Surgical Records/patient_795__Surgery.txt" },
      { id: "surg-3703", name: "patient_3703__ENT.txt", type: "file", ext: "txt", importance: 0.7, group: "surgical", path: "/Surgical Records/patient_3703__ENT.txt" },
    ],
  },
  {
    id: "cat-diagnostic",
    name: "Clinical Assessments",
    type: "folder",
    ext: "folder",
    importance: 0.8,
    group: "diagnostic",
    children: [
      { id: "diag-4113", name: "patient_4113__Consult.txt", type: "file", ext: "txt", importance: 0.95, group: "diagnostic", path: "/Clinical Assessments/patient_4113__Consult.txt" },
      { id: "diag-1581", name: "patient_1581__Radiology.txt", type: "file", ext: "txt", importance: 0.7, group: "diagnostic", path: "/Clinical Assessments/patient_1581__Radiology.txt" },
      { id: "diag-1901", name: "patient_1901__Pediatrics.txt", type: "file", ext: "txt", importance: 0.75, group: "diagnostic", path: "/Clinical Assessments/patient_1901__Pediatrics.txt" },
    ],
  },
];

// ─── Flatten tree into nodes list for graph ─────────────────────────
const flattenTree = (tree) => {
  const nodes = [];
  tree.forEach((item) => {
    const { children, path, ...nodeData } = item;
    nodes.push({ ...nodeData, path: path || `/${item.name}` });
    if (children) {
      children.forEach((child) => {
        nodes.push(child);
      });
    }
  });
  return nodes;
};

export const graphNodes = flattenTree(fileTree);

export const graphLinks = [
  // ── Pulmonary hierarchy (Chest X-Rays) ──
  { source: "cat-pulmonary", target: "xray-0006" },
  { source: "cat-pulmonary", target: "xray-0007" },
  { source: "cat-pulmonary", target: "xray-0009" },
  { source: "cat-pulmonary", target: "xray-0010" },
  { source: "xray-0006", target: "xray-0007" },   // same imaging series
  { source: "xray-0009", target: "xray-0010" },   // same imaging series

  // ── Infectious hierarchy (Pneumonia bacterial images) ──
  { source: "cat-infectious", target: "pneum-103" },
  { source: "cat-infectious", target: "pneum-104" },
  { source: "cat-infectious", target: "pneum-109a" },
  { source: "cat-infectious", target: "pneum-109b" },
  { source: "pneum-103", target: "pneum-104" },     // similar bacterial type
  { source: "pneum-109a", target: "pneum-109b" },   // same patient (person109)

  // ── Cardiac hierarchy (Heart Sounds) ──
  { source: "cat-cardiac", target: "heart-1" },
  { source: "cat-cardiac", target: "heart-2" },
  { source: "cat-cardiac", target: "heart-3" },
  { source: "cat-cardiac", target: "heart-4" },
  { source: "cat-cardiac", target: "heart-5" },
  { source: "heart-1", target: "heart-2" },   // baseline recording set
  { source: "heart-3", target: "heart-4" },   // baseline recording set
  { source: "heart-4", target: "heart-5" },   // baseline recording set

  // ── Surgical hierarchy ──
  { source: "cat-surgical", target: "surg-593" },
  { source: "cat-surgical", target: "surg-795" },
  { source: "cat-surgical", target: "surg-3703" },

  // ── Diagnostic hierarchy ──
  { source: "cat-diagnostic", target: "diag-4113" },
  { source: "cat-diagnostic", target: "diag-1581" },
  { source: "cat-diagnostic", target: "diag-1901" },

  // ═══════════ CROSS-GROUP LINKS (semantic relationships) ═══════════

  // Pneumonia images ↔ Chest X-Rays (both are chest/lung imaging)
  { source: "pneum-103", target: "xray-0006" },
  { source: "pneum-104", target: "xray-0007" },
  { source: "cat-infectious", target: "cat-pulmonary" },  // category-level

  // Lung lobectomy surgery ↔ Chest X-Rays (lung mass, pre-op imaging)
  { source: "surg-593", target: "cat-pulmonary" },
  { source: "surg-593", target: "xray-0009" },

  // Lymphoma consult (patient_4113) has pneumothorax history → pulmonary
  { source: "diag-4113", target: "cat-pulmonary" },

  // Lymphoma consult (HIV+) → infection/pneumonia susceptibility
  { source: "diag-4113", target: "cat-infectious" },

  // AV fistula vascular surgery → cardiovascular/cardiac domain
  { source: "surg-795", target: "cat-cardiac" },

  // ENT surgery (tonsillectomy) ↔ Pediatric (throat-related)
  { source: "surg-3703", target: "diag-1901" },

  // Lung lobectomy ↔ Lymphoma consult (oncology overlap)
  { source: "surg-593", target: "diag-4113" },

  // Radiology report ↔ Chest X-Rays (imaging modalities)
  { source: "diag-1581", target: "cat-pulmonary" },

  // Pediatric assessment ↔ Radiology (musculoskeletal overlap)
  { source: "diag-1901", target: "diag-1581" },

  // Pneumonia cases ↔ Lung lobectomy (pulmonary pathology)
  { source: "pneum-109a", target: "surg-593" },

  // Heart sounds ↔ Lymphoma consult (chest pain/cardio symptoms)
  { source: "heart-1", target: "diag-4113" },
];

// ─── Mock file content for preview ──────────────────────────────────
export const mockFileContent = {
  "xray-0006": `[CHEST X-RAY — IM-0006-0001.jpeg]

Modality: Digital Radiograph (PA view)
Body Part: Chest
Clinical Indication: Routine screening

FINDINGS:
Heart size normal. Mediastinal contours unremarkable.
Lungs are clear bilaterally. No infiltrates, effusions,
or pneumothorax identified. Costophrenic angles are sharp.
Osseous structures are intact.

IMPRESSION: Normal chest radiograph.`,

  "xray-0007": `[CHEST X-RAY — IM-0007-0001.jpeg]

Modality: Digital Radiograph (PA view)
Body Part: Chest
Clinical Indication: Pre-operative clearance

FINDINGS:
Cardiomediastinal silhouette within normal limits.
No acute pulmonary disease. No pleural effusion.
No focal consolidation or mass lesion identified.

IMPRESSION: No acute cardiopulmonary abnormality.`,

  "xray-0009": `[CHEST X-RAY — IM-0009-0001.jpeg]

Modality: Digital Radiograph (PA & Lateral views)
Body Part: Chest
Clinical Indication: Follow-up imaging

FINDINGS:
Heart size is at the upper limits of normal.
Lungs demonstrate no acute infiltrate.
Small linear density at the right base likely
represents minor atelectasis.

IMPRESSION: No significant interval change.`,

  "xray-0010": `[CHEST X-RAY — IM-0010-0001.jpeg]

Modality: Digital Radiograph (AP view)
Body Part: Chest
Clinical Indication: Cough evaluation

FINDINGS:
Mild perihilar bronchial wall thickening bilaterally.
No focal consolidation. No pleural effusion.
Heart size within normal limits.

IMPRESSION: Findings suggestive of mild bronchitis.
Clinical correlation recommended.`,

  "pneum-103": `[PNEUMONIA — Bacterial Infection Image]

Patient: Person 103
Image ID: bacteria_490.jpeg
Classification: PNEUMONIA (Bacterial)

Clinical Context:
Chest radiograph demonstrating right lower lobe
consolidation consistent with bacterial pneumonia.
Air bronchograms visible within opacity.
Organism: Streptococcus pneumoniae (suspected)

Used for AI training dataset — labeled as positive
for bacterial pneumonia detection.`,

  "pneum-104": `[PNEUMONIA — Bacterial Infection Image]

Patient: Person 104
Image ID: bacteria_492.jpeg
Classification: PNEUMONIA (Bacterial)

Clinical Context:
Left lower lobe consolidation with air bronchograms.
Consistent with community-acquired bacterial pneumonia.
Adjacent pleural thickening noted.

Training label: BACTERIA_POSITIVE`,

  "pneum-109a": `[PNEUMONIA — Bacterial Infection Image]

Patient: Person 109 (Image 1 of 2)
Image ID: bacteria_517.jpeg
Classification: PNEUMONIA (Bacterial)

Clinical Context:
Bilateral patchy consolidation, more prominent
on the right. Suggests multifocal bacterial pneumonia.
This patient has two sequential images for comparison.

Training label: BACTERIA_POSITIVE`,

  "pneum-109b": `[PNEUMONIA — Bacterial Infection Image]

Patient: Person 109 (Image 2 of 2)
Image ID: bacteria_523.jpeg
Classification: PNEUMONIA (Bacterial)

Clinical Context:
Follow-up image showing interval progression
of bilateral consolidation. Comparison with
bacteria_517 shows worsening right-sided opacity.

Training label: BACTERIA_POSITIVE`,

  "heart-1": `[HEART SOUND RECORDING]

File: ElevenLabs_2026-02-15T01_37_16_Rachel.mp3
Type: Normal Heart Sound (S1-S2)
Generated: 2026-02-15 01:37

Auscultation Site: Mitral area (apex)
Heart Rate: ~72 bpm
Duration: 5 seconds

Description:
Normal first (S1) and second (S2) heart sounds.
No murmurs, gallops, or rubs detected.
Regular rhythm, normal splitting of S2.

Classification: NORMAL`,

  "heart-2": `[HEART SOUND RECORDING]

File: ElevenLabs_2026-02-15T01_37_58_Rachel.mp3
Type: Normal Heart Sound (S1-S2)
Generated: 2026-02-15 01:37

Auscultation Site: Aortic area
Heart Rate: ~68 bpm
Duration: 5 seconds

Description:
Clear S1 and S2 sounds. Normal intensity.
No systolic or diastolic murmurs appreciated.
Physiologic splitting present.

Classification: NORMAL`,

  "heart-3": `[HEART SOUND RECORDING]

File: ElevenLabs_2026-02-15T01_38_38_Rachel.mp3
Type: Normal Heart Sound (S1-S2)
Generated: 2026-02-15 01:38

Auscultation Site: Tricuspid area
Heart Rate: ~76 bpm
Duration: 5 seconds

Description:
Normal heart sounds without extra sounds.
S1 louder than S2 at this location.
No clicks or snaps.

Classification: NORMAL`,

  "heart-4": `[HEART SOUND RECORDING]

File: ElevenLabs_2026-02-15T01_39_11_Rachel.mp3
Type: Normal Heart Sound (S1-S2)
Generated: 2026-02-15 01:39

Auscultation Site: Pulmonic area
Heart Rate: ~70 bpm
Duration: 5 seconds

Description:
Normal S1-S2 with clear pulmonic component.
Physiologic splitting of S2 with respiration.
No murmurs or adventitious sounds.

Classification: NORMAL`,

  "heart-5": `[HEART SOUND RECORDING]

File: ElevenLabs_2026-02-15T01_39_35_Rachel.mp3
Type: Normal Heart Sound (S1-S2)
Generated: 2026-02-15 01:39

Auscultation Site: Erb's point
Heart Rate: ~74 bpm
Duration: 5 seconds

Description:
Normal S1-S2 at Erb's point.
No diastolic murmur or extra heart sounds.
Rhythm regular.

Classification: NORMAL`,

  "surg-593": `OPERATION:
1. Right upper lung lobectomy.
2. Mediastinal lymph node dissection.

ANESTHESIA: General endotracheal with dual-lumen tube
and thoracic epidural.

PROCEDURE: Patient placed in left lateral decubitus
position. Incision below angle of scapula, 6th interspace
entered. A 4x4cm mass identified in right upper lobe
with no other metastatic disease palpable.

Pulmonary artery branches to RUL ligated with suture
and clips. Pulmonary vein branch ligated with 0 silk.
Bronchus stapled with TA-30 and divided.
Mediastinal lymph node dissection performed.

#32-Fr anterior and posterior chest tubes placed.
Patient tolerated procedure well.`,

  "surg-795": `PREPROCEDURE DIAGNOSIS: End-stage renal disease.

PROCEDURES PERFORMED:
1. Left arm fistulogram.
2. PTA of proximal and distal cephalic vein.
3. Ultrasound-guided access of brachiocephalic fistula.

INDICATION: 38yo female with left upper arm brachiocephalic
fistula (transposed). Recent fistulogram showed proximal
stenosis. Poor flow on follow-up, high-grade stenosis on
duplex US near brachial anastomosis.

TECHNIQUE: Standard balloon angioplasty with 5x20mm balloon
followed by 4x20mm cutting balloon for residual stenosis.
Post-procedure: excellent results, palpable thrill restored.

IMPRESSION: Successful angioplasty of high-grade cephalic
vein stenosis. No contrast extravasation.`,

  "surg-3703": `PROCEDURE: Tonsillectomy and Adenoidectomy
ANESTHESIA: General endotracheal

DESCRIPTION:
McIvor mouth gag placed. Two #12-Fr red rubber catheters
placed in nasal passages for soft palate retraction.
Nasopharynx inspected with laryngeal mirror.

Adenoid tissue fulgurated with suction Bovie at 35.
Anterior tonsillar pillars infiltrated with 0.5%
Marcaine and epinephrine.

Tonsils ablated bilaterally using radiofrequency wand
(coag mode 3, ablation mode 9).

Patient tolerated procedure well.`,

  "diag-4113": `CHIEF COMPLAINT: Newly diagnosed T-cell lymphoma.

HPI: 40yo male with left submandibular swelling x6 weeks.
Initially treated as tooth abscess. Night sweats x1 month,
overwhelming fatigue, mild chest pain, decreased appetite.

PMH:
- HIV diagnosed 2000
- Mononucleosis (2000)
- Spontaneous pneumothorax (R lung 1989, L lung 1990)
- Shingles (2003, 2009)

FAMILY HX: Mother - non-small cell lung cancer (nonsmoker).
Sister - EBV positive. Grandfather - melanoma.

SOCIAL HX: 13.5 pack-year smoking history (quarter pack/day).
Self-employed antiquing. Formerly nurses' aide.

ROS: Night sweats, chest pain, fatigue, headaches, SOB,
occasional loose stools, fevers, depression.`,

  "diag-1581": `RADIOLOGY REPORT — MRI Elbow

FINDINGS:
Diffuse subcutis edema along posteromedial elbow.
Enlargement with hyperintense signal of ulnar nerve
within cubital tunnel — ulnar nerve neuritis.

Inflammation with mild laxity of epicondylo-olecranon
ligament. Mild epimysial sheath edema of pronator teres.
Minimal common extensor tendon tendinitis.

IMPRESSION:
1. Ulnar nerve neuritis (possible subluxing nerve)
2. Mild lateral epicondylitis
3. Pronator teres epimysial strain
4. Brachialis tendon peritendinous edema
5. No mass lesion identified`,

  "diag-1901": `PEDIATRIC RHEUMATOLOGY CLINIC

PATIENT: 7yo male
CC: Joint pain (fingers, elbows, neck) x2 months

HPI: Previously well child, pain onset 2 months ago.
Would cry from pain. Currently symptoms improving.
No swelling except elbow (per referring MD).
Active child, no GI symptoms, no fevers.

PMH: Seasonal allergies (on Claritin). No surgeries.
FHx: Grandmother — arthritis. Father — psoriasis.

EXAM: Afebrile. No joint swelling or tenderness today.
Full ROM all joints. Muscle strength 5/5.

LABS: Sed rate 2, RF 6, ANA negative, CRP 7.1.

ASSESSMENT: Likely reactive arthritis. Family history
notable for psoriatic arthritis/psoriasis. Labs and
exam normal today. Observe, return if symptoms recur.`,
};

// ─── Neighbor map builder ───────────────────────────────────────────
export const buildNeighborMap = (links) => {
  const map = new Map();
  links.forEach((l) => {
    const sid = typeof l.source === "object" ? l.source.id : l.source;
    const tid = typeof l.target === "object" ? l.target.id : l.target;
    if (!map.has(sid)) map.set(sid, new Set());
    if (!map.has(tid)) map.set(tid, new Set());
    map.get(sid).add(tid);
    map.get(tid).add(sid);
  });
  return map;
};
