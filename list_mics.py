import speech_recognition as sr

for i, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"{i}: {name}")

print("\nSet MIC_DEVICE_INDEX in config.py to the number of the mic you want to use.")