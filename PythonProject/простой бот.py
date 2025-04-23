import speech_recognition as sr
import pyttsx3
import time
import webbrowser
# Инициализация движка для синтеза речи
engine = pyttsx3.init()


def speak(text):
    """Функция для воспроизведения текста"""
    engine.say(text)
    engine.runAndWait()


def listen():
    """Функция для распознавания речи"""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Слушаю...")
        audio = r.listen(source)

    try:
        text = r.recognize_google(audio, language="ru-RU")
        print(f"Вы сказали: {text}")
        return text.lower()
    except sr.UnknownValueError:
        speak("Я вас не поняла, повторите пожалуйста")
        return listen()
    except sr.RequestError:
        speak("Проблемы с подключением к сервису распознавания")
        return None


def main():
    speak("Привет! Я Анфиса голосовой бот. Максим Как я могу вам помочь?")

    while True:
        command = listen()

        if command:
            if "привет" in command:
                speak("Приветствую!")
            elif "как дела" in command:
                speak("У меня всё отлично, спасибо!")

            elif "сколько время" in command:
                current_time = time.strftime("%H:%M")
                speak(f"Сейчас {current_time}")
            elif "пока" in command or "до свидания" in command:
                speak("До свидания! Хорошего дня!")
                break
            else:
                speak("Я не понимаю эту команду. Попробуйте что-то другое.")


if __name__ == "__main__":
    main()