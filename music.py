import whisper

file = "audio1.mp4"

model = whisper.load_model("base")
text = model.transcribe(file)["text"]

with open("output.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("\nTranscript: \n", text)

# https://www.facebook.com/share/v/19cxG26LYS/