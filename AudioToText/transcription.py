
from faster_whisper import WhisperModel

# Choix du modèle : "tiny" ou "base" (très légers)
model_size = "base"

# Chargement du modèle (device="cpu" pour fonctionner sans GPU)
model = WhisperModel(model_size, device="cpu", compute_type="int8")

# Nom de votre fichier audio
audio_file = "test.mp3"  

print(f"Transcription de {audio_file} en cours...")


segments, info = model.transcribe(audio_file)

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
