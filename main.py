from tkinter import Tk, messagebox, filedialog, Button, Label
from PIL import Image, ImageTk
import os, shutil

class GImageCategorizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Gading's Image Categorizer v1.0")
        self.root.geometry("1600x800")
        self.current_image_index = 0
        self.current_image_path = ""
        self.original_file_path = ""
        self.image_list = []
        self.folder_a = "infected"
        self.folder_b = "normal"
        self.photo = None
        
        self.image_label = Label(self.root)
        self.image_label.pack()

        self.select_button = Button(self.root, text="Select Directory", command=self.select_directory)
        self.folder_a_button = Button(self.root, text="Infected", state="disabled")
        self.folder_b_button = Button(self.root, text="Normal", state="disabled")
        self.select_button.pack()
        self.folder_a_button.pack()
        self.folder_b_button.pack()

        self.image_status = Label(self.root, text="0 images left")
        self.image_status.pack()

        self.root.bind('<Key>', self.handle_key_event)
        self.root.focus_set()

    def set_config(self):
        self.destination_folder_a = os.path.join(self.input_directory, self.folder_a)
        self.destination_folder_b = os.path.join(self.input_directory, self.folder_b)
        os.makedirs(self.destination_folder_a, exist_ok=True)
        os.makedirs(self.destination_folder_b, exist_ok=True)
        self.folder_a_button.config(state="normal", command=self.move_to_a) # Dont forget to change if want to Copy/Move
        self.folder_b_button.config(state="normal", command=self.move_to_b) # Dont forget to change if want to Copy/Move

    def select_directory(self):
        self.input_directory = filedialog.askdirectory()
        if self.input_directory:
            self.image_list = os.listdir(self.input_directory)
            # print(len(self.image_list))
            # self.image_list = [x for x in self.image_list if x.endswith(('.JPG', '.jpeg','.png'))]
            self.image_list = [os.path.join(self.input_directory, filename) for filename in self.image_list if filename.endswith(('.JPG', '.jpeg','.png'))]
            self.set_config()
            self.display_image()
            self.images_left = len(self.image_list)
            self.image_status['text'] = f"{self.images_left} images left" # Move feature only (not copy feature)

    def display_image(self):
        if self.current_image_index < len(self.image_list):
            self.current_image_path = self.image_list[self.current_image_index]
            image = Image.open(self.current_image_path)
            # image.thumbnail(image.size)
            image = image.resize((int(image.size[0] * 1.75), int(image.size[1] * 1.75)))
            self.photo = ImageTk.PhotoImage(image)
            self.image_label.configure(image=self.photo)
            # self.image_label.image = photo
        else:
            messagebox.showinfo("Gading's Image Categorizer v1.0", "No more images.")

    def copy_to_a(self):
        return self.copy_to_folder(self.destination_folder_a)
    
    def copy_to_b(self):
        return self.copy_to_folder(self.destination_folder_b)

    def copy_to_folder(self, destination_folder):
        destination_path = os.path.join(destination_folder, os.path.basename(self.current_image_path))
        shutil.copy2(self.original_file_path, destination_path)
        self.current_image_index += 1
        self.display_image()

    def move_to_a(self):
        return self.move_to_folder(self.destination_folder_a)

    def move_to_b(self):
        return self.move_to_folder(self.destination_folder_b)

    def move_to_folder(self, destination_folder):
        destination_path = os.path.join(destination_folder, os.path.basename(self.current_image_path))
        try:
            os.rename(self.current_image_path, destination_path)
        except OSError as e:
            messagebox.showerror("Image Viewer", f"Error moving image: {str(e)}")
        else:
            self.current_image_index += 1
            self.images_left -= 1
            self.image_status['text'] = "{} images left".format(self.images_left)
            self.display_image()

    def handle_key_event(self, event):
        if event.keysym == 'o':
            self.move_to_a()
        elif event.keysym == 'p':
            self.move_to_b()

if __name__ == '__main__':
    root = Tk()
    app = GImageCategorizer(root)
    root.configure(background="black")
    root.mainloop()
