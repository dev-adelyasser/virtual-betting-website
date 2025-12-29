import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
from datetime import datetime, timedelta
import hashlib

class SecretManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Time-Locked Secret Manager")
        self.root.geometry("700x500")
        
        self.data_file = "secrets.json"
        self.secrets = self.load_secrets()
        
        self.create_widgets()
        
    def load_secrets(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_secrets(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.secrets, f, indent=2)
    
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title = ttk.Label(main_frame, text="Time-Locked Secret Manager", 
                         font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="Add New Secret", 
                  command=self.add_secret_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Reveal Secret", 
                  command=self.reveal_secret_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Secret", 
                  command=self.delete_secret_dialog).pack(side=tk.LEFT, padx=5)
        
        # Secrets list
        list_label = ttk.Label(main_frame, text="Stored Secrets:", 
                              font=('Arial', 12))
        list_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.secrets_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                         height=15, font=('Arial', 10))
        self.secrets_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.secrets_listbox.yview)
        
        self.refresh_list()
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
    
    def refresh_list(self):
        self.secrets_listbox.delete(0, tk.END)
        for name, data in self.secrets.items():
            unlock_time = datetime.fromisoformat(data['unlock_time'])
            status = "🔓 Ready" if datetime.now() >= unlock_time else "🔒 Locked"
            time_str = unlock_time.strftime("%Y-%m-%d %H:%M")
            self.secrets_listbox.insert(tk.END, 
                f"{status} | {name} | Unlock: {time_str} | {len(data['questions'])} questions")
    
    def add_secret_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Secret")
        dialog.geometry("500x400")
        
        ttk.Label(dialog, text="Secret Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Secret String:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        secret_entry = ttk.Entry(dialog, width=40, show="*")
        secret_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Wait Time (minutes):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        time_entry = ttk.Entry(dialog, width=40)
        time_entry.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Questions (one per line):").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=5)
        questions_text = tk.Text(dialog, width=40, height=5)
        questions_text.grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Answers (one per line):").grid(row=4, column=0, sticky=tk.NW, padx=5, pady=5)
        answers_text = tk.Text(dialog, width=40, height=5)
        answers_text.grid(row=4, column=1, padx=5, pady=5)
        
        def save_secret():
            name = name_entry.get().strip()
            secret = secret_entry.get().strip()
            try:
                wait_minutes = int(time_entry.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Wait time must be a number")
                return
            
            questions = [q.strip() for q in questions_text.get("1.0", tk.END).split('\n') if q.strip()]
            answers = [a.strip() for a in answers_text.get("1.0", tk.END).split('\n') if a.strip()]
            
            if not name or not secret:
                messagebox.showerror("Error", "Name and secret are required")
                return
            
            if len(questions) != len(answers):
                messagebox.showerror("Error", "Number of questions must match number of answers")
                return
            
            if name in self.secrets:
                messagebox.showerror("Error", "Secret with this name already exists")
                return
            
            unlock_time = datetime.now() + timedelta(minutes=wait_minutes)
            
            # Hash the secret for storage
            hashed_secret = hashlib.sha256(secret.encode()).hexdigest()
            
            self.secrets[name] = {
                'secret': secret,  # In production, encrypt this
                'hashed_secret': hashed_secret,
                'unlock_time': unlock_time.isoformat(),
                'questions': questions,
                'answers': answers
            }
            
            self.save_secrets()
            self.refresh_list()
            dialog.destroy()
            messagebox.showinfo("Success", f"Secret '{name}' added. Unlocks at {unlock_time.strftime('%Y-%m-%d %H:%M')}")
        
        ttk.Button(dialog, text="Save Secret", command=save_secret).grid(row=5, column=0, columnspan=2, pady=10)
    
    def reveal_secret_dialog(self):
        selection = self.secrets_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a secret from the list")
            return
        
        selected_text = self.secrets_listbox.get(selection[0])
        name = selected_text.split(" | ")[1]
        
        if name not in self.secrets:
            messagebox.showerror("Error", "Secret not found")
            return
        
        secret_data = self.secrets[name]
        unlock_time = datetime.fromisoformat(secret_data['unlock_time'])
        
        # Check if time has passed
        if datetime.now() < unlock_time:
            remaining = unlock_time - datetime.now()
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            messagebox.showwarning("Locked", 
                f"Secret is still locked. Time remaining: {hours}h {minutes}m {seconds}s")
            return
        
        # Ask questions
        self.ask_questions(name, secret_data)
    
    def ask_questions(self, name, secret_data):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Unlock: {name}")
        dialog.geometry("500x400")
        
        ttk.Label(dialog, text=f"Answer the questions to reveal the secret:", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        answer_entries = []
        
        for i, question in enumerate(secret_data['questions']):
            frame = ttk.Frame(dialog)
            frame.pack(fill=tk.X, padx=20, pady=5)
            
            ttk.Label(frame, text=f"Q{i+1}: {question}").pack(anchor=tk.W)
            entry = ttk.Entry(frame, width=50)
            entry.pack(fill=tk.X, pady=2)
            answer_entries.append(entry)
        
        def check_answers():
            correct = True
            for i, entry in enumerate(answer_entries):
                if entry.get().strip().lower() != secret_data['answers'][i].lower():
                    correct = False
                    break
            
            if correct:
                dialog.destroy()
                self.show_secret(name, secret_data['secret'])
            else:
                messagebox.showerror("Wrong Answer", "One or more answers are incorrect. Try again.")
        
        ttk.Button(dialog, text="Submit Answers", command=check_answers).pack(pady=20)
    
    def show_secret(self, name, secret):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Secret Revealed: {name}")
        dialog.geometry("400x200")
        
        ttk.Label(dialog, text="🎉 Secret Revealed!", 
                 font=('Arial', 14, 'bold')).pack(pady=20)
        
        secret_frame = ttk.Frame(dialog, relief=tk.SOLID, borderwidth=2)
        secret_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        
        secret_label = ttk.Label(secret_frame, text=secret, 
                                font=('Arial', 12), wraplength=350)
        secret_label.pack(padx=10, pady=10)
        
        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(secret)
            messagebox.showinfo("Copied", "Secret copied to clipboard")
        
        ttk.Button(dialog, text="Copy to Clipboard", command=copy_to_clipboard).pack(pady=5)
    
    def delete_secret_dialog(self):
        selection = self.secrets_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a secret from the list")
            return
        
        selected_text = self.secrets_listbox.get(selection[0])
        name = selected_text.split(" | ")[1]
        
        if messagebox.askyesno("Confirm Delete", f"Delete secret '{name}'?"):
            del self.secrets[name]
            self.save_secrets()
            self.refresh_list()
            messagebox.showinfo("Deleted", f"Secret '{name}' has been deleted")

if __name__ == "__main__":
    root = tk.Tk()
    app = SecretManager(root)
    root.mainloop()
