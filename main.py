from tkinter import Tk, messagebox, filedialog, Button, Label
from PIL import Image, ImageTk
import os, shutil

class GImageCategorizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Gading's Image Categorizer v1.0")
        self.root.geometry("800x500")
        self.current_image_index = 0
        self.current_image_filename = ""
        self.original_file_path = ""
        self.image_list = []
        self.folder_a = "infected"
        self.folder_b = "normal"
        
        self.image_label = Label(self.root)
        self.image_label.pack()

        self.select_button = Button(self.root, text="Select Directory", command=self.select_directory)
        self.folder_a_button = Button(self.root, text="Infected", command=self.copy_to_folder(self.destination_folder_a), state="disabled")
        self.folder_b_button = Button(self.root, text="Normal", command=self.copy_to_folder(self.destination_folder_b), state="disabled")
        self.select_button.pack()
        self.folder_a_button.pack()
        self.folder_b_button.pack()

    def select_directory(self):
        self.input_directory = filedialog.askdirectory()
        if self.input_directory:
            self.image_list = os.listdir(self.input_directory)
            print(len(self.image_list))
            self.image_list = [x for x in self.image_list if x.endswith(('.JPG', '.jpeg','.png'))]
            os.makedirs(self.folder_a, exist_ok=True)
            os.makedirs(self.folder_b, exist_ok=True)
            self.destination_folder_a = os.path.join(self.input_directory, self.folder_a)
            self.destination_folder_b = os.path.join(self.input_directory, self.folder_b)
            self.folder_a_button.config(state="normal")
            self.folder_b_button.config(state="normal")
            self.display_image()

    def display_image(self):
        if self.current_image_index < len(self.image_list):
            self.current_image_filename = self.image_list[self.current_image_index]
            self.original_file_path = os.path.join(self.input_directory, self.current_image_filename)
            image = Image.open(self.original_file_path)
            image.thumbnail(image.size)
            photo = ImageTk.PhotoImage(image)
            self.image_label.configure(image=photo)
            self.image_label.image = photo
        else:
            messagebox.showinfo("Gading's Image Categorizer v1.0", "No more images.")

    def copy_to_folder(self, destination_folder):
        destination_path = os.path.join(destination_folder, self.current_image_filename)
        shutil.copy2(self.original_file_path, destination_path)
        self.current_image_index += 1
        self.display_image()

    # def move_to_folder_a(self):
    #     self.move_image_to_folder('infected')

    # def move_to_folder_b(self):
    #     self.move_image_to_folder('normal')

    # def move_image_to_folder(self, folder_name):
    #     image_path = self.image_list[self.current_image_index]
    #     destination_folder = os.path.join(self.input_directory, folder_name)
    #     # os.makedirs(destination_folder, exist_ok=True)
    #     destination_path = os.path.join(destination_folder, image_path)
    #     os.rename(image_path, destination_path)
    #     self.current_image_index += 1
    #     self.display_image()

if __name__ == '__main__':
    root = Tk()
    app = GImageCategorizer(root)
    root.mainloop()
