import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import serial.tools.list_ports
import pyvisa
import time
import re
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Example usage

class BoardController:
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        try:
            self.sa = self.rm.open_resource("USB0::0x1AB1::0x0968::RSA5F234800168::INSTR")
        except Exception as e:
            print("Could not connect to spectrum analyzer:", e)
            self.sa = None

    def setup_and_measure(self, freq_str):
        results = {"frequency": None, "power": None}
        try:
            match = re.search(r"([\d.]+)", freq_str)
            freq_mhz = float(match.group(1)) if match else 0.0
            freq_hz_str = f"{freq_mhz}E6"

            self.sa.write(f":SENSe:FREQuency:CENTer {freq_hz_str}")
            time.sleep(0.2)
            read_freq_hz = float(self.sa.query(":SENSe:FREQuency:CENTer?").strip())
            read_freq_mhz = read_freq_hz / 1e6
            if abs(read_freq_mhz - freq_mhz) >= 0.01:
                print("Frequency mismatch")
                return None

            self.sa.write(":SENSe:FREQuency:SPAN 2E6")
            time.sleep(0.1)

            self.sa.write(":TRACe1:MODE WRITe")
            time.sleep(0.1)

            self.sa.write(":INITiate:CONTinuous OFF")
            self.sa.write(":INITiate:IMMediate")
            self.sa.query("*OPC?")
            time.sleep(0.2)

            self.sa.write(":CALCulate:MARKer1:STATe ON")
            self.sa.write(":CALCulate:MARKer1:TRACe 1")
            time.sleep(0.1)
            self.sa.write(":CALCulate:MARKer1:MAXimum")
            self.sa.query("*OPC?")
            time.sleep(0.6)

            freqs, powers = [], []
            for _ in range(5):
                freq = float(self.sa.query(":CALCulate:MARKer1:X?").strip()) / 1e6
                power = float(self.sa.query(":CALCulate:MARKer1:Y?").strip())
                freqs.append(freq)
                powers.append(power)
                time.sleep(0.1)

            avg_freq = sum(freqs) / len(freqs)
            avg_power = sum(powers) / len(powers)

            results["frequency"] = avg_freq
            results["power"] = avg_power

            print(f"\nAverage Frequency: {avg_freq:.3f} MHz")
            print(f"Average Amplitude: {avg_power:.7f} dBm\n")

            return results

        except Exception as e:
            print("Error during measurement:", e)
            return None

class FrequencySelectionGUI:
    board_controller = BoardController()
    board_entries = []
    result_labels = []
    tx_results_data = []

    @staticmethod
    def load_top_bar(root, title_text="TESTING",align="center"):
        top_bar = tk.Frame(root, bg="#004a99", height=70)
        top_bar.pack(fill='x', side='top')
        top_bar.pack_propagate(False)

        try:
            logo_image = Image.open("C:\\Users\\paras\\Desktop\\ATE GUI\\logo.png")
            logo_image = logo_image.resize((60, 60), Image.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo_image)
            logo_label = tk.Label(top_bar, image=logo_photo, bg="#004a99")
            logo_label.image = logo_photo
            logo_label.pack(side="right", padx=(10, 10), pady=5)
        except Exception as e:
            print("Logo not loaded:", e)

        title_label = tk.Label(top_bar, text=title_text, bg="#004a99", fg="white",
                               font=("Times New Roman", 36, "bold"))
        if align == "left":
            title_label.pack(side="left",padx=20,pady=5)
        else:
            title_label.pack(pady=5)
        
    @staticmethod
    def load_bottom_bar(root):
        bottom_bar = tk.Frame(root, bg="#004a99", height=70)
        bottom_bar.pack(fill="x", side="bottom")
        bottom_bar.pack_propagate(False)

        footer_label = tk.Label(bottom_bar, text="Paras Anti-Drone Technologies Pvt Ltd.",
                                bg="#004a99", fg="white", font=("Times New Roman", 15))
        footer_label.pack(side="left", padx=10, pady=5)

    @staticmethod
    def create_main_screen(root):
        for widget in root.winfo_children():
            widget.destroy()

        root.title("Paras Anti-Drone Technologies Pvt Ltd.")
        root.geometry("1200x700")
        root.configure(bg='white')
        root.iconbitmap("C:\\Users\\paras\\Desktop\\ATE GUI\\icon.ico")

        FrequencySelectionGUI.load_top_bar(root, "Paras Anti-Drone Technologies Pvt Ltd.", align="left")

        center_frame= tk.Frame(root, bg="white")
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(center_frame, text="AUTOMATED TEST EQUIPMENT", font=("Times New Roman", 32), bg="white").pack(pady=(0, 60))

        dropdown_frame = tk.Frame(center_frame, bg="white")
        dropdown_frame.pack(pady=10)

        ports = [port.device for port in serial.tools.list_ports.comports()]
        if not ports:
            ports = ["No ports found"]

        def create_port_selector(label_text):
            frame = tk.Frame(dropdown_frame, bg="white")
            frame.pack(side="left", padx=20)
            label = tk.Label(frame, text=label_text, bg="white", font=("Times New Roman", 14))
            label.pack()
            combo = ttk.Combobox(frame, values=ports, state="readonly", font=("Times New Roman", 12))
            combo.pack()
            if ports[0] != "No ports found":
                combo.current(0)
            return combo

        FrequencySelectionGUI.tx_port_combo = create_port_selector("TX Port")
        FrequencySelectionGUI.ber_tx_port_combo = create_port_selector("BER TX Port")
        FrequencySelectionGUI.ber_rx_port_combo = create_port_selector("BER RX Port")

        tk.Button(center_frame, text="Start", font=("Times New Roman", 20, "bold"),
                bg="#004a99", fg="white", padx=20, pady=10,
                command=lambda: FrequencySelectionGUI.create_sa_gui(root)).pack(pady=25)

        FrequencySelectionGUI.load_bottom_bar(root)

    @staticmethod
    def create_back_button(root, command):
        back_frame = tk.Frame(root, bg="white")
        back_frame.pack(fill="x")

        back_button = tk.Button(
            back_frame, text="Back", font=("Times New Roman", 12, "bold"),
            bg="#004a99", fg="white", padx=10, pady=5,
            command=command
        )
        back_button.pack(side="left", padx=10, pady=(5, 0))

    @staticmethod
    def create_sa_gui(root):
        for widget in root.winfo_children():
            widget.destroy()

        FrequencySelectionGUI.load_top_bar(root, "TESTING")
        FrequencySelectionGUI.create_back_button(root, lambda: FrequencySelectionGUI.create_main_screen(root))

        content_frame = tk.Frame(root, bg="white")
        content_frame.pack(fill="both", expand=True)

        content_frame.grid_columnconfigure(0, weight=1, uniform="group1")
        content_frame.grid_columnconfigure(1, weight=0)
        content_frame.grid_columnconfigure(2, weight=1, uniform="group1")

        tx_test_frame = tk.Frame(content_frame, bg="white", padx=20, pady=20)
        tx_test_frame.grid(row=1, column=0, sticky="nsew")

        separator = tk.Frame(content_frame, bg="black", width=3)
        separator.grid(row=1, column=1, sticky="ns")

        rx_test_frame = tk.Frame(content_frame, bg="white", padx=20, pady=20)
        rx_test_frame.grid(row=1, column=2, sticky="nsew")

        tk.Label(tx_test_frame, text="TX TEST", font=("Times New Roman", 30, "bold"), bg="white").grid(row=0, column=0, pady=(10, 20))

        boards = ["Board 1", "Board 2", "Board 3", "Board 4"]
        tx_test_frame.grid_columnconfigure(0, weight=1)

        FrequencySelectionGUI.board_entries = []
        FrequencySelectionGUI.tx_results_data = []

        for i, board in enumerate(boards):
            frame = tk.Frame(tx_test_frame, bg="white", bd=1, relief=tk.SOLID, padx=10, pady=10)
            frame.grid(row=i + 1, column=0, sticky="ew", pady=5)
            tx_test_frame.grid_rowconfigure(i + 1, weight=1)

            selected_var = tk.IntVar()

            tk.Checkbutton(frame, variable=selected_var, onvalue=1, offvalue=0,
                       bg="white", activebackground="lightgrey", selectcolor="white").grid(row=0, column=0, sticky="nw")

            tk.Label(frame, text=board, font=("Times New Roman", 20, "bold"), bg="white").grid(
            row=0, column=1, rowspan=4, sticky="nw", padx=5)

            tk.Label(frame, text="Board Name:", font=("Times New Roman", 14), bg="white").grid(row=0, column=2, sticky="w")
            board_name_entry = tk.Entry(frame, font=("Times New Roman", 12), width=25, bg="#f2f2f2")
            board_name_entry.insert(0, f"Board {i+1}")
            board_name_entry.grid(row=0, column=3, padx=5, pady=2, sticky="w")

            tk.Label(frame, text="Frequency Band:", font=("Times New Roman", 14), bg="white").grid(row=1, column=2, sticky="w")
            freq_band_frame = tk.Frame(frame, bg="white")
            freq_band_frame.grid(row=1, column=3, columnspan=2, sticky="w")

            freq_band_combo = ttk.Combobox(freq_band_frame, values=["VHF", "UHF"], font=("Times New Roman", 12), width=10)
            freq_band_combo.pack(side="left", padx=(0, 5))

            freq_range_entry = tk.Entry(freq_band_frame, font=("Times New Roman", 12), width=20, state="readonly", bg="#f2f2f2")
            freq_range_entry.pack(side="left")

            tk.Label(frame, text="Center Frequency:", font=("Times New Roman", 14), bg="white").grid(row=2, column=2, sticky="w")
            center_freq_entry = tk.Entry(frame, font=("Times New Roman", 12), width=25, bg="#f2f2f2")
            center_freq_entry.grid(row=2, column=3, padx=5, pady=2, sticky="w")

            def on_band_select(event, combo=freq_band_combo, entry=freq_range_entry, center_entry=center_freq_entry):
                selected = combo.get()
                entry.config(state="normal")
                entry.delete(0, tk.END)
                center_entry.delete(0, tk.END)
                if selected == "VHF":
                    entry.insert(0, "136 MHz - 172 MHz")
                    center_entry.insert(0, "155 MHz")
                elif selected == "UHF":
                    entry.insert(0, "403 MHz - 527 MHz")
                    center_entry.insert(0, "446 MHz")
                entry.config(state="readonly")

            freq_band_combo.bind("<<ComboboxSelected>>", on_band_select)
            freq_band_combo.set("VHF")
            on_band_select(None, combo=freq_band_combo, entry=freq_range_entry, center_entry=center_freq_entry)

            FrequencySelectionGUI.board_entries.append({
                "selected": selected_var,
                "board_name": board_name_entry,
                "center_freq": center_freq_entry,
                "freq_band": freq_band_combo
            })

        # RX TEST
        tk.Label(rx_test_frame, text="RX TEST", font=("Times New Roman", 30, "bold"), bg="white").pack(pady=(10, 40))

        attenuator_frame = tk.Frame(rx_test_frame, bg="white")
        attenuator_frame.pack(pady=10, anchor="w")
        tk.Label(attenuator_frame, text="Attenuator (dB):", font=("Times New Roman", 16), bg="white").pack(side="left")
        FrequencySelectionGUI.attenuator_entry = tk.Entry(attenuator_frame, font=("Times New Roman", 16), width=20, bg="#f2f2f2")
        FrequencySelectionGUI.attenuator_entry.pack(side="left", padx=5)

        file_frame = tk.Frame(rx_test_frame, bg="white")
        file_frame.pack(pady=10, anchor="w")
        tk.Label(file_frame, text="Choose File:", font=("Times New Roman", 16), bg="white").pack(side="left")
        FrequencySelectionGUI.file_path_var = tk.StringVar()
        file_entry = tk.Entry(file_frame, textvariable=FrequencySelectionGUI.file_path_var,
                          font=("Times New Roman", 14), width=30, bg="#f2f2f2", state="readonly")
        file_entry.pack(side="left", padx=5)
    
        def browse_file():
            file_path = filedialog.askopenfilename(title="Select File", filetypes=[("All Files", "*.*")])
            if file_path:
                FrequencySelectionGUI.file_path_var.set(os.path.basename(file_path))  # show only file name

        tk.Button(file_frame, text="Browse", font=("Times New Roman", 12), command=browse_file).pack(side="left")

        start_button = tk.Button(
            content_frame, text="Start", font=("Times New Roman", 14, "bold"),
            bg="#004a99", fg="white", padx=15, pady=5,
            command=lambda: FrequencySelectionGUI.process_boards(root)
        )
        start_button.grid(row=2, column=0, columnspan=3, pady=10)

    @staticmethod
    def update_frequency_range(combo, entry):
        selected = combo.get()
        entry.config(state="normal")
        entry.delete(0, tk.END)
        if selected == "VHF":
            entry.insert(0, "136 MHz - 172 MHz")
        elif selected == "UHF":
            entry.insert(0, "403 MHz - 527 MHz")
        entry.config(state="readonly")

    @staticmethod
    def process_boards(root):
        FrequencySelectionGUI.tx_results_data = []

        for i, board in enumerate(FrequencySelectionGUI.board_entries):
            if board["selected"].get() == 1 :
                board_name = board["board_name"].get()
                freq = board["center_freq"].get()

                if not freq:
                    messagebox.showwarning("Missing Data", f"Please enter center frequency for Board {i+1}")
                    return

                results = FrequencySelectionGUI.board_controller.setup_and_measure(freq)
                if not results:
                    messagebox.showerror("SCPI Error", f"Could not set frequency or measure Board {i+1}")
                    return

                FrequencySelectionGUI.tx_results_data.append({
                    "board_name": board_name or f"Board {i+1}",
                    "frequency": results["frequency"],
                    "power": results["power"]
                })

        FrequencySelectionGUI.create_result_screen(root)

    @staticmethod

    def create_result_screen(root):
        for widget in root.winfo_children():
            widget.destroy()

        FrequencySelectionGUI.load_top_bar(root, "RESULTS")
        FrequencySelectionGUI.create_back_button(root, lambda: FrequencySelectionGUI.create_sa_gui(root))

        content_frame = tk.Frame(root, bg="white")
        content_frame.pack(fill="both", expand=True)
        content_frame.grid_columnconfigure(0, weight=1, uniform="group1")
        content_frame.grid_columnconfigure(1, weight=0)
        content_frame.grid_columnconfigure(2, weight=1, uniform="group1")
        content_frame.grid_rowconfigure(0, weight=1)

        left_frame = tk.Frame(content_frame, bg="white", padx=20, pady=20)
        left_frame.grid(row=0, column=0, sticky="nsew")

        separator = tk.Frame(content_frame, bg="black", width=3)
        separator.grid(row=0, column=1, sticky="ns")

        right_frame = tk.Frame(content_frame, bg="white", padx=20, pady=20)
        right_frame.grid(row=0, column=2, sticky="nsew")

        tk.Label(left_frame, text="TX RESULT", font=("Times New Roman", 30, "bold"), bg="white").pack(pady=10)
        for result in FrequencySelectionGUI.tx_results_data:
            text = (
                f"{result['board_name']}\n"
                f"Freq: {result['frequency']:.3f} MHz\n"
                f"Power: {result['power']:.3f} dBm\n"
            )
            tk.Label(left_frame, text=text, font=("Times New Roman", 14), bg="white", justify="left").pack(anchor="w", pady=5)

        tk.Label(right_frame, text="RX RESULT", font=("Times New Roman", 30, "bold"), bg="white").pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    FrequencySelectionGUI.create_main_screen(root)
    root.iconbitmap(resource_path("C:\\Users\\paras\\Desktop\\ATE GUI\\icon.ico"))
    root.mainloop()

