

import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image
from pyzbar.pyzbar import decode
from qreader import QReader
import numpy as np
import cv2
import threading
import json



def main():
    CONFIG_FILE = 'config.json'


    def load_config():
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as file:
                return json.load(file)
        return {
            "input_folder": "",
            "output_folder": ""
        }


    def save_config(config):
        with open(CONFIG_FILE, 'w') as file:
            json.dump(config, file)


    def select_input_folder():
        folder = filedialog.askdirectory()
        if folder:
            input_folder_var.set(folder)
            config['input_folder'] = folder
            save_config(config)


    def select_output_folder():
        folder = filedialog.askdirectory()
        if folder:
            output_folder_var.set(folder)
            config['output_folder'] = folder
            save_config(config)


    def decode_qr_code(image_path):
        # Сначала пытаемся использовать pyzbar
        image = Image.open(image_path)
        decoded_objects = decode(image)
        for obj in decoded_objects:
            return obj.data.decode("utf-8")

        #   Если pyzbar не справился, используем QReader
        np_image = np.array(image)
        cv2_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
        decoded_text = qr_reader.detect_and_decode(image=cv2_image)
        if len(decoded_text) != 0 and decoded_text[0] is not None:
            return decoded_text[0]

        return None


    def process_photos():
        app.update_idletasks()

        input_folder = input_folder_var.get()
        output_folder = output_folder_var.get()

        if not os.path.exists(input_folder):
            messagebox.showerror("Ошибка", "Указанная папка с фотографиями не существует")
            return

        if not os.path.exists(output_folder):
            messagebox.showerror("Ошибка", "Указанная папка для сортированных фотографий не существует")
            return

        # Заблокируем кнопку "Начать сортировку", чтобы избежать множественных запусков
        start_button.config(state=tk.DISABLED)

        def sorting_thread():
            status_var.set(f"Сортировка файлов по дате")
            files = sorted(os.listdir(input_folder), key=lambda x: os.path.getmtime(os.path.join(input_folder, x)))
            status_var.set(f"Начинаем сортировку по qr")

            successfully_sorted = 0
            failed_files = []

            for i in range(0, len(files), 2):

                photo_path = os.path.join(input_folder, files[i + 1])
                qr_path = os.path.join(input_folder, files[i])

                if not os.path.isfile(photo_path) or not os.path.isfile(qr_path):
                    messagebox.showerror("Ошибка", f"Файл {files[i + 1]} или {files[i]} не является файлом")
                    failed_files.append(files[i + 1] if os.path.isfile(photo_path) else files[i])
                    continue

                try:
                    folder_name = decode_qr_code(qr_path)
                except Exception as e:
                    failed_files.append(files[i])
                    continue

                if not folder_name:
                    failed_files.append(files[i])
                    continue

                target_folder = os.path.join(output_folder, folder_name)

                if not os.path.exists(target_folder):
                    os.makedirs(target_folder)
                shutil.move(photo_path, os.path.join(target_folder, os.path.basename(photo_path)))
                os.remove(qr_path)  # Удаление QR-кода после успешного перемещения фотографии

                successfully_sorted += 1

                if (i // 2 + 1) % 50 == 0:
                    status_var.set(f"Обработано {i // 2 + 1} фотографий")
                    app.update_idletasks()

            start_button.config(state=tk.NORMAL)
            unsuccessfully_sorted = len(failed_files)

            # Отображение результатов в новом окне
            results_window = tk.Toplevel(app)
            results_window.title("Результаты сортировки")

            tk.Label(results_window, text=f"Успешно отсортировано: {successfully_sorted} фотографий").pack(padx=10, pady=5)
            tk.Label(results_window, text=f"Не удалось отсортировать: {unsuccessfully_sorted} фотографий").pack(padx=10,
                                                                                                                pady=5)

            if failed_files:
                def show_failed_files():
                    failed_files_window = tk.Toplevel(app)
                    failed_files_window.title("Список файлов с ошибками")
                    text_area = scrolledtext.ScrolledText(failed_files_window, width=60, height=10)
                    text_area.pack(padx=10, pady=10)
                    for file in failed_files:
                        text_area.insert(tk.END, f"{file}\n")

                tk.Button(results_window, text="Подробнее", command=show_failed_files).pack(padx=10, pady=10)

            status_var.set("Обработка завершена")

        threading.Thread(target=sorting_thread).start()



    qr_reader = QReader(model_size="n")
    app = tk.Tk()
    app.title("Сортировщик фотографий по QR-коду")

    config = load_config()

    # папки по умолчанию
    input_folder_var = tk.StringVar(value=config.get("input_folder", ""))
    output_folder_var = tk.StringVar(value=config.get("output_folder", ""))

    status_var = tk.StringVar(value="")

    tk.Label(app, text="Папка с фотографиями:").grid(row=0, column=0, padx=10, pady=10)
    tk.Entry(app, textvariable=input_folder_var, width=50).grid(row=0, column=1, padx=10, pady=10)
    tk.Button(app, text="Выбрать", command=select_input_folder).grid(row=0, column=2, padx=10, pady=10)

    tk.Label(app, text="Папка для сортированных фото:").grid(row=1, column=0, padx=10, pady=10)
    tk.Entry(app, textvariable=output_folder_var, width=50).grid(row=1, column=1, padx=10, pady=10)
    tk.Button(app, text="Выбрать", command=select_output_folder).grid(row=1, column=2, padx=10, pady=10)

    tk.Label(app, textvariable=status_var).grid(row=2, column=0, columnspan=3, padx=10, pady=10)

    start_button = tk.Button(app, text="Начать сортировку", command=process_photos)
    start_button.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

    app.mainloop()


if __name__ == "__main__":
    main()
