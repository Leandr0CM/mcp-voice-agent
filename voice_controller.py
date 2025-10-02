# voice_controller.py

import speech_recognition as sr
import pyttsx3
import re

class VoiceController:
    """Gerencia entrada de voz (STT) e saída de voz (TTS)"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.tts_engine = pyttsx3.init()
        
        # Configurações de voz
        voices = self.tts_engine.getProperty('voices')
        # Tenta usar voz em português (se disponível)
        for voice in voices:
            if 'portuguese' in voice.name.lower() or 'brazil' in voice.name.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
        
        self.tts_engine.setProperty('rate', 150)  # Velocidade
        self.tts_engine.setProperty('volume', 0.9)  # Volume
        
        # Calibração do microfone
        print("🎤 Calibrando microfone para ruído ambiente...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✓ Microfone calibrado e pronto!\n")

    def speak(self, text: str):
        """Fala o texto usando TTS"""
        # Remove emojis e caracteres especiais para o TTS
        clean_text = re.sub(r'[^\w\s,.\-!?()]', '', text)
        clean_text = clean_text.replace('✓', '').replace('✗', '')
        print(f"🤖 MCP: {text}")
        self.tts_engine.say(clean_text)
        self.tts_engine.runAndWait()

    def listen(self) -> str | None:
        """Escuta e converte fala em texto"""
        with self.microphone as source:
            print("👂 Ouvindo...")
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=20)
                print("🔄 Processando fala...")
                text = self.recognizer.recognize_google(audio, language="pt-BR")
                print(f"✓ Você disse: '{text}'")
                return text
            except sr.WaitTimeoutError:
                print("⏱️  Timeout: nenhum comando detectado")
                return None
            except sr.UnknownValueError:
                self.speak("Desculpe, não entendi. Pode repetir?")
                return None
            except sr.RequestError as e:
                error_msg = f"Erro no serviço de reconhecimento: {e}"
                print(f"❌ {error_msg}")
                self.speak("Estou com problemas no serviço de voz.")
                return None