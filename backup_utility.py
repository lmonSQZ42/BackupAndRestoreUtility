import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import json
import sys
import datetime

# Determine the application path for portable .exe compatibility
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    application_path = os.path.dirname(sys.executable)
else:
    # Running as a normal Python script
    application_path = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(application_path, "backuputility.json")

class BackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Backup And Restore Saved Data")
        self.root.geometry("850x450")
        self.root.minsize(850, 450)
        self.root.resizable(True, True)

        self.config = {
            "profiles": {"Default": {"source_file": "", "target_folder": ""}},
            "current_profile": "Default"
        }

        self.is_loading_profile = True
        self.unsaved_changes = False

        self.source_file = tk.StringVar()
        self.target_folder = tk.StringVar()
        self.active_profile = tk.StringVar(value="Default")
        self.backup_mode = tk.StringVar(value="File")

        self.slot_labels = [tk.StringVar(value="Not set") for _ in range(3)]

        # Traces for change tracking and label updates
        self.source_file.trace_add("write", self.on_var_change)
        self.target_folder.trace_add("write", self.on_var_change)
        self.source_file.trace_add("write", self.update_slot_labels)
        self.target_folder.trace_add("write", self.update_slot_labels)

        self.load_config()
        if "window_geometry" in self.config:
            self.root.geometry(self.config["window_geometry"])
            
        self.hotkeys_enabled = tk.BooleanVar(value=self.config.get("hotkeys_enabled", True))
        self.create_widgets()
        self.populate_profiles()
        self.apply_current_profile()
        self.apply_hotkeys()
        self.is_loading_profile = False
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.config["window_geometry"] = self.root.geometry()
        self.save_config()
        self.root.destroy()

    def create_widgets(self):
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # --- Left Panel (Navigation) ---
        left_frame = tk.Frame(main_paned, width=200, bg="#e8e8e8", relief=tk.SUNKEN, borderwidth=1)
        main_paned.add(left_frame, minsize=180)

        tk.Label(left_frame, text="Backup Profiles", bg="#e8e8e8", font=("Arial", 11, "bold")).pack(pady=10)

        self.profile_listbox = tk.Listbox(left_frame, exportselection=False, font=("Arial", 10), selectbackground="#0078D7")
        self.profile_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.profile_listbox.bind('<<ListboxSelect>>', self.on_profile_select)

        btn_frame = tk.Frame(left_frame, bg="#e8e8e8")
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(btn_frame, text="Add Profile", command=self.add_profile).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tk.Button(btn_frame, text="Delete", command=self.delete_profile).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # --- Right Panel (Content) ---
        right_frame = tk.Frame(main_paned)
        main_paned.add(right_frame, minsize=550)

        # Header
        header_frame = tk.Frame(right_frame)
        header_frame.pack(fill=tk.X, pady=15)
        tk.Label(header_frame, text="Active Profile:", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(20, 5))
        tk.Label(header_frame, textvariable=self.active_profile, font=("Arial", 12), fg="blue").pack(side=tk.LEFT)

        # Mode Selection
        mode_frame = tk.Frame(right_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(mode_frame, text="Backup Type:").pack(side=tk.LEFT, padx=(20, 5))
        tk.Radiobutton(mode_frame, text="File", variable=self.backup_mode, value="File", command=self.on_mode_change).pack(side=tk.LEFT)
        tk.Radiobutton(mode_frame, text="Folder", variable=self.backup_mode, value="Folder", command=self.on_mode_change).pack(side=tk.LEFT)

        # Paths Section
        path_frame = tk.Frame(right_frame)
        path_frame.pack(fill=tk.X, pady=5)
        path_frame.grid_columnconfigure(1, weight=1)

        tk.Label(path_frame, text="Original Source:").grid(row=0, column=0, padx=20, pady=10, sticky="e")
        tk.Entry(path_frame, textvariable=self.source_file, state='readonly').grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        tk.Button(path_frame, text="Browse", command=self.browse_source).grid(row=0, column=2, padx=(10, 5), pady=10)
        tk.Button(path_frame, text="Open", command=self.open_source).grid(row=0, column=3, padx=(5, 10), pady=10)

        tk.Label(path_frame, text="Backup Folder Location:").grid(row=1, column=0, padx=20, pady=5, sticky="e")
        tk.Entry(path_frame, textvariable=self.target_folder, state='readonly').grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        tk.Button(path_frame, text="Browse", command=self.browse_target).grid(row=1, column=2, padx=(10, 5), pady=5)
        tk.Button(path_frame, text="Open", command=self.open_target).grid(row=1, column=3, padx=(5, 10), pady=5)

        # Slots Section
        slots_frame = tk.Frame(right_frame)
        slots_frame.pack(fill=tk.BOTH, expand=True, pady=15)
        slots_frame.grid_columnconfigure(4, weight=1)

        tk.Label(slots_frame, text="Backup & Restore Slots", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=5, pady=(0, 10))

        for i in range(1, 4):
            tk.Label(slots_frame, text=f"Slot {i}:", font=("Arial", 10, "bold")).grid(row=i, column=0, padx=20, pady=10, sticky="e")
            tk.Button(slots_frame, text="Backup", width=12, command=lambda slot=i: self.backup(slot)).grid(row=i, column=1, padx=5, pady=10)
            tk.Button(slots_frame, text="Restore", width=12, command=lambda slot=i: self.restore(slot)).grid(row=i, column=2, padx=5, pady=10)
            tk.Button(slots_frame, text="Delete", width=8, command=lambda slot=i: self.delete_slot(slot)).grid(row=i, column=3, padx=5, pady=10)
            # Display target filename dynamically
            tk.Label(slots_frame, textvariable=self.slot_labels[i-1], fg="gray", anchor="w").grid(row=i, column=4, padx=10, pady=10, sticky="ew")

        # Action Buttons
        action_frame = tk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.btn_save = tk.Button(action_frame, text="Save Settings", command=self.save_settings, state=tk.DISABLED, width=15)
        self.btn_save.pack(side=tk.RIGHT, padx=(5, 20))
        
        self.btn_cancel = tk.Button(action_frame, text="Cancel", command=self.cancel_settings, state=tk.DISABLED, width=15)
        self.btn_cancel.pack(side=tk.RIGHT, padx=5)

        # Hotkeys UI
        tk.Checkbutton(action_frame, text="Enable Hotkeys", variable=self.hotkeys_enabled, command=self.toggle_hotkeys).pack(side=tk.LEFT, padx=(20, 5))
        tk.Button(action_frame, text="Hotkeys", command=self.open_hotkey_settings).pack(side=tk.LEFT, padx=5)

    # --- Profile Management ---
    def populate_profiles(self):
        self.profile_listbox.delete(0, tk.END)
        for profile_name in self.config["profiles"]:
            self.profile_listbox.insert(tk.END, profile_name)

        current = self.config["current_profile"]
        try:
            idx = list(self.config["profiles"].keys()).index(current)
            self.profile_listbox.selection_set(idx)
        except ValueError:
            pass

    def apply_current_profile(self):
        self.is_loading_profile = True
        current = self.config["current_profile"]
        self.active_profile.set(current)
        profile_data = self.config["profiles"].get(current, {"source_file": "", "target_folder": "", "backup_mode": "File"})

        self.backup_mode.set(profile_data.get("backup_mode", "File"))
        self.source_file.set(profile_data.get("source_file", ""))
        self.target_folder.set(profile_data.get("target_folder", ""))
        self.update_slot_labels()
        
        self.unsaved_changes = False
        if hasattr(self, 'btn_save'):
            self.update_save_buttons_state()
        self.is_loading_profile = False

    def on_profile_select(self, event):
        selection = self.profile_listbox.curselection()
        if not selection:
            return
        selected_profile = self.profile_listbox.get(selection[0])
        if selected_profile != self.config["current_profile"]:
            if getattr(self, 'unsaved_changes', False):
                ans = messagebox.askyesnocancel("Unsaved Changes", f"You have unsaved changes in profile '{self.config['current_profile']}'. Do you want to save them before switching?")
                if ans is True:
                    self.save_settings()
                elif ans is False:
                    # discard
                    pass
                else:
                    # cancel switch
                    self.populate_profiles()
                    return

            self.config["current_profile"] = selected_profile
            self.apply_current_profile()
            self.save_config()

    def add_profile(self):
        if getattr(self, 'unsaved_changes', False):
            ans = messagebox.askyesnocancel("Unsaved Changes", f"You have unsaved changes in profile '{self.config['current_profile']}'. Do you want to save them before adding a new profile?")
            if ans is True:
                self.save_settings()
            elif ans is False:
                pass
            else:
                return

        new_name = simpledialog.askstring("Add Profile", "Enter new profile name:", parent=self.root)
        if new_name:
            new_name = new_name.strip()
            if not new_name:
                return
            if new_name in self.config["profiles"]:
                messagebox.showerror("Error", "Profile name already exists!")
                return

            self.config["profiles"][new_name] = {"source_file": "", "target_folder": "", "backup_mode": "File"}
            self.config["current_profile"] = new_name
            self.populate_profiles()
            self.apply_current_profile()
            self.save_config()

    def delete_profile(self):
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showinfo("Select", "Please select a profile to delete.")
            return

        selected_profile = self.profile_listbox.get(selection[0])

        if len(self.config["profiles"]) <= 1:
            messagebox.showerror("Error", "Cannot delete the last remaining profile.")
            return

        if selected_profile == self.config["current_profile"] and getattr(self, 'unsaved_changes', False):
            # If we are deleting the active profile and it has unsaved changes, they will be discarded anyway
            pass

        confirm = messagebox.askyesno("Confirm", f"Are you sure you want to delete profile '{selected_profile}'?")
        if confirm:
            del self.config["profiles"][selected_profile]
            new_active = list(self.config["profiles"].keys())[0]
            self.config["current_profile"] = new_active
            self.populate_profiles()
            self.apply_current_profile()
            self.save_config()

    # --- Dynamic Updates ---
    def on_mode_change(self, *args):
        if not getattr(self, 'is_loading_profile', True):
            self.source_file.set("")
            self.update_slot_labels()
            self.mark_unsaved()

    def on_var_change(self, *args):
        if not getattr(self, 'is_loading_profile', True):
            self.mark_unsaved()

    def mark_unsaved(self):
        if not self.unsaved_changes:
            self.unsaved_changes = True
            self.update_save_buttons_state()

    def update_save_buttons_state(self):
        state = tk.NORMAL if self.unsaved_changes else tk.DISABLED
        if hasattr(self, 'btn_save'):
            self.btn_save.config(state=state)
            self.btn_cancel.config(state=state)

    def save_settings(self):
        current = self.config["current_profile"]
        if current in self.config["profiles"]:
            self.config["profiles"][current]["backup_mode"] = self.backup_mode.get()
            self.config["profiles"][current]["source_file"] = self.source_file.get()
            self.config["profiles"][current]["target_folder"] = self.target_folder.get()
            self.save_config()
            self.unsaved_changes = False
            self.update_save_buttons_state()
            messagebox.showinfo("Settings Saved", f"Settings for profile '{current}' have been saved.")

    def cancel_settings(self):
        self.apply_current_profile()

    def update_slot_labels(self, *args):
        source = self.source_file.get()
        target_dir = self.target_folder.get()
        if not source:
            for i in range(3):
                self.slot_labels[i].set("Not set")
            return
            
        current = self.config.get("current_profile", "Default")
        last_restored_info = self.config["profiles"].get(current, {}).get("last_restored", {})
        
        base_name = os.path.basename(source.rstrip('/\\'))
        for i in range(1, 4):
            if self.backup_mode.get() == "File":
                name, ext = os.path.splitext(base_name)
                slot_filename = f"{name}_slot{i}{ext}"
            else:
                slot_filename = f"{base_name}_slot{i}"
            
            label_text = f"\u2192 {slot_filename}"
            if target_dir and os.path.exists(target_dir):
                target_path = os.path.join(target_dir, slot_filename)
                if os.path.exists(target_path):
                    try:
                        mtime = os.path.getmtime(target_path)
                        date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                        label_text += f"  (Backed up: {date_str})"
                        
                        restored_ts = last_restored_info.get(str(i))
                        if restored_ts:
                            restored_date_str = datetime.datetime.fromtimestamp(restored_ts).strftime('%Y-%m-%d %H:%M')
                            label_text += f" | Restored: {restored_date_str}"
                    except Exception:
                        pass
            
            self.slot_labels[i-1].set(label_text)

    # --- File Operations ---
    def open_source(self):
        source = self.source_file.get()
        if source and os.path.exists(source):
            try:
                if self.backup_mode.get() == "File":
                    folder = os.path.dirname(source)
                    if os.path.exists(folder):
                        os.startfile(folder)
                else:
                    os.startfile(source)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open location:\n{e}")

    def open_target(self):
        target = self.target_folder.get()
        if target and os.path.exists(target):
            try:
                os.startfile(target)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open location:\n{e}")

    def browse_source(self):
        if self.backup_mode.get() == "File":
            filepath = filedialog.askopenfilename(title="Select Original File")
            if filepath:
                self.source_file.set(filepath)
        else:
            folderpath = filedialog.askdirectory(title="Select Original Folder")
            if folderpath:
                self.source_file.set(folderpath)

    def browse_target(self):
        folderpath = filedialog.askdirectory(title="Select Backup Folder Location")
        if folderpath:
            self.target_folder.set(folderpath)

    def get_slot_filename(self, slot):
        source = self.source_file.get()
        if not source:
            return None
        base_name = os.path.basename(source.rstrip('/\\'))
        if self.backup_mode.get() == "File":
            name, ext = os.path.splitext(base_name)
            return f"{name}_slot{slot}{ext}"
        else:
            return f"{base_name}_slot{slot}"

    def backup(self, slot):
        source = self.source_file.get()
        target_dir = self.target_folder.get()

        if not source or not os.path.exists(source):
            messagebox.showerror("Error", "Please select a valid Original Source first.")
            return

        if not target_dir or not os.path.exists(target_dir):
            messagebox.showerror("Error", "Please select a valid Backup Folder Location first.")
            return

        slot_filename = self.get_slot_filename(slot)
        target_path = os.path.join(target_dir, slot_filename)

        try:
            if self.backup_mode.get() == "File":
                shutil.copy2(source, target_path)
                messagebox.showinfo("Success", f"File successfully backed up to Slot {slot}!\n\nSaved as: {slot_filename}")
            else:
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)
                shutil.copytree(source, target_path)
                messagebox.showinfo("Success", f"Folder successfully backed up to Slot {slot}!\n\nSaved as: {slot_filename}")
            
            current = self.config["current_profile"]
            if "last_restored" in self.config["profiles"][current]:
                if str(slot) in self.config["profiles"][current]["last_restored"]:
                    del self.config["profiles"][current]["last_restored"][str(slot)]
                    self.save_config()
                    
            self.update_slot_labels()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during backup:\n{str(e)}")

    def delete_slot(self, slot):
        target_dir = self.target_folder.get()

        if not target_dir:
            messagebox.showerror("Error", "Please select the Backup Folder Location first.")
            return

        slot_filename = self.get_slot_filename(slot)
        if not slot_filename:
            return

        backup_path = os.path.join(target_dir, slot_filename)

        if not os.path.exists(backup_path):
            messagebox.showinfo("Info", f"No backup found in Slot {slot} to delete.")
            return

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the backup in Slot {slot}?\n\nThis cannot be undone.")
        if not confirm:
            return

        try:
            if os.path.isfile(backup_path):
                os.remove(backup_path)
            elif os.path.isdir(backup_path):
                shutil.rmtree(backup_path)
            
            # Remove restored history if exists
            current = self.config["current_profile"]
            if "last_restored" in self.config["profiles"][current]:
                if str(slot) in self.config["profiles"][current]["last_restored"]:
                    del self.config["profiles"][current]["last_restored"][str(slot)]
                    self.save_config()

            self.update_slot_labels()
            messagebox.showinfo("Success", f"Backup in Slot {slot} deleted successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete backup:\n{str(e)}")

    def restore(self, slot):
        source = self.source_file.get()
        target_dir = self.target_folder.get()

        if not source:
            messagebox.showerror("Error", "Please select the Original Source location to restore to.")
            return

        if not target_dir:
            messagebox.showerror("Error", "Please select the Backup Folder Location where the backups are stored.")
            return

        slot_filename = self.get_slot_filename(slot)
        backup_path = os.path.join(target_dir, slot_filename)

        if not os.path.exists(backup_path):
            messagebox.showerror("Error", f"No backup found in Slot {slot} to restore from.\n\nLooking for: {slot_filename}")
            return

        mode = self.backup_mode.get()
        confirm = messagebox.askyesno("Confirm Restore", f"Are you sure you want to restore from Slot {slot}?\n\nThis will OVERWRITE your current Original {mode}.")
        if not confirm:
            return

        try:
            if mode == "File":
                shutil.copy2(backup_path, source)
                messagebox.showinfo("Success", f"File successfully restored from Slot {slot}!")
            else:
                if os.path.exists(source):
                    shutil.rmtree(source)
                shutil.copytree(backup_path, source)
                messagebox.showinfo("Success", f"Folder successfully restored from Slot {slot}!")
            
            current = self.config["current_profile"]
            if "last_restored" not in self.config["profiles"][current]:
                self.config["profiles"][current]["last_restored"] = {}
            self.config["profiles"][current]["last_restored"][str(slot)] = datetime.datetime.now().timestamp()
            self.save_config()
            self.update_slot_labels()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during restore:\n{str(e)}")

    # --- Persistence ---
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    if "profiles" in data:
                        self.config = data
                    else:
                        # Migrate from old flat structure to profiles structure
                        self.config["profiles"]["Default"] = {
                            "source_file": data.get("source_file", ""),
                            "target_folder": data.get("target_folder", ""),
                            "backup_mode": "File"
                        }
                        self.config["current_profile"] = "Default"
            except Exception as e:
                print(f"Failed to load config: {e}")

        if "hotkeys" not in self.config:
            self.config["hotkeys"] = {
                "backup_1": "KP_1",
                "backup_2": "KP_2",
                "backup_3": "KP_3",
                "restore_1": "KP_7",
                "restore_2": "KP_8",
                "restore_3": "KP_9",
                "add_profile": "KP_0",
                "save_settings": "KP_Add",
                "cancel_settings": "KP_Subtract"
            }
        if "hotkeys_enabled" not in self.config:
            self.config["hotkeys_enabled"] = True

    # --- Hotkeys ---
    def toggle_hotkeys(self):
        self.config["hotkeys_enabled"] = self.hotkeys_enabled.get()
        self.save_config()

    def open_hotkey_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Customize Hotkeys")
        win.geometry("450x450")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Click 'Change' then press a new key to assign it.", pady=10).pack()

        frame = tk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.hotkey_vars = {}
        
        actions_info = [
            ("backup_1", "Backup Slot 1"),
            ("backup_2", "Backup Slot 2"),
            ("backup_3", "Backup Slot 3"),
            ("restore_1", "Restore Slot 1"),
            ("restore_2", "Restore Slot 2"),
            ("restore_3", "Restore Slot 3"),
            ("add_profile", "Add Profile"),
            ("save_settings", "Save Settings"),
            ("cancel_settings", "Cancel Settings")
        ]

        for idx, (act, desc) in enumerate(actions_info):
            tk.Label(frame, text=desc, font=("Arial", 10)).grid(row=idx, column=0, sticky="w", pady=5)
            current_key = self.config["hotkeys"].get(act, "None")
            var = tk.StringVar(value=current_key)
            self.hotkey_vars[act] = var
            
            lbl = tk.Label(frame, textvariable=var, width=15, relief="sunken", bg="white", font=("Arial", 10))
            lbl.grid(row=idx, column=1, padx=15, pady=5)
            
            btn = tk.Button(frame, text="Change", command=lambda a=act, l=lbl: self.assign_hotkey(win, a, l))
            btn.grid(row=idx, column=2, pady=5)

        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=15)
        
        def clear_all():
            for act, var in self.hotkey_vars.items():
                var.set("None")
                self.config["hotkeys"][act] = "None"
                
        tk.Button(btn_frame, text="Clear All", width=15, command=clear_all).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Save & Close", width=15, command=lambda: [self.apply_hotkeys(), self.save_config(), win.destroy()]).pack(side=tk.LEFT, padx=10)

    def assign_hotkey(self, win, act, lbl):
        lbl.config(bg="yellow")
        self.hotkey_vars[act].set("Press a key...")
        
        def on_key(event):
            win.unbind("<Key>")
            lbl.config(bg="white")
            keysym = event.keysym
            self.hotkey_vars[act].set(keysym)
            self.config["hotkeys"][act] = keysym
            
        win.bind("<Key>", on_key)

    def apply_hotkeys(self):
        if hasattr(self, '_global_hotkey_bind_id'):
            try:
                self.root.unbind_all("<KeyPress>", self._global_hotkey_bind_id)
            except: pass
            
        def global_key_handler(event):
            if not self.hotkeys_enabled.get():
                return
            # Do not trigger hotkeys if an entry or text widget has focus
            if event.widget.winfo_class() in ("Entry", "Text"):
                return
            # Optional: Do not trigger if a dialog (Toplevel) is currently open
            if event.widget.winfo_toplevel() != self.root:
                return
                
            hotkeys = self.config.get("hotkeys", {})
            for action_name, keysym in hotkeys.items():
                if keysym and keysym != "None" and event.keysym == keysym:
                    self.trigger_action(action_name)
                    break
                    
        self._global_hotkey_bind_id = self.root.bind_all("<KeyPress>", global_key_handler)

    def trigger_action(self, act):
        if act == "backup_1": self.backup(1)
        elif act == "backup_2": self.backup(2)
        elif act == "backup_3": self.backup(3)
        elif act == "restore_1": self.restore(1)
        elif act == "restore_2": self.restore(2)
        elif act == "restore_3": self.restore(3)
        elif act == "add_profile": self.add_profile()
        elif act == "save_settings":
            if getattr(self, 'btn_save', None) and self.btn_save['state'] == tk.NORMAL:
                self.save_settings()
        elif act == "cancel_settings":
            if getattr(self, 'btn_cancel', None) and self.btn_cancel['state'] == tk.NORMAL:
                self.cancel_settings()

if __name__ == "__main__":
    root = tk.Tk()
    app = BackupApp(root)
    root.mainloop()
