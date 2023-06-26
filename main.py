import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os

class GImageCategorizer:
    def __init__(self, root):
        self.root = root
        self.current_image_index = 0
        self.image_list = []
        self.load_images()
        
        self.image_label = tk.Label(root)
        self.image_label.pack()

        self.folder_a_button = tk.Button(root, text="Move to folder A", command=self.move_to_folder_a)
        self.folder_a_button.pack(side=tk.LEFT)

        self.folder_b_button = tk.Button(root, text="Move to folder B", command=self.move_to_folder_b)
        self.folder_b_button.pack(side=tk.LEFT)
        
        self.display_image()

    def load_images(self):
        # Update the directory path according to your image folder
        image_directory = 'path/to/your/image/folder'
        self.image_list = os.listdir(image_directory)
        self.image_list = [file for file in self.image_list if file.endswith(('.png', '.jpg', '.jpeg'))]

    def display_image(self):
        if self.current_image_index < len(self.image_list):
            image_path = self.image_list[self.current_image_index]
            image = Image.open(image_path)
            image.thumbnail((500, 500))  # Resize image if necessary
            photo = ImageTk.PhotoImage(image)
            self.image_label.configure(image=photo)
            self.image_label.image = photo
        else:
            messagebox.showinfo("Image Viewer", "No more images.")
    
    def move_to_folder_a(self):
        self.move_image_to_folder('FolderA')

    def move_to_folder_b(self):
        self.move_image_to_folder('FolderB')

    def move_image_to_folder(self, folder_name):
        image_path = self.image_list[self.current_image_index]
        destination_folder = f'path/to/destination/folder/{folder_name}'
        os.makedirs(destination_folder, exist_ok=True)
        destination_path = os.path.join(destination_folder, image_path)
        os.rename(image_path, destination_path)
        self.current_image_index += 1
        self.display_image()

if __name__ == '__main__':
    root = tk.Tk()
    app = GImageCategorizer(root)
    root.mainloop()
