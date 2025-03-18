import tkinter as tk
from tkinter import ttk, messagebox
import serial
import pynmea2
import threading
from datetime import datetime


class GPSGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GPS 데이터 모니터")
        self.root.geometry("600x400")

        self.serial_port = None
        self.is_running = False

        self.setup_gui()

    def setup_gui(self):
        # COM 포트 설정 프레임
        port_frame = ttk.LabelFrame(self.root, text="연결 설정", padding="5")
        port_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(port_frame, text="COM 포트:").pack(side="left", padx=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var)
        self.port_combo["values"] = [f"COM{i}" for i in range(1, 11)]
        self.port_combo.pack(side="left", padx=5)

        self.connect_btn = ttk.Button(
            port_frame, text="연결", command=self.toggle_connection
        )
        self.connect_btn.pack(side="left", padx=5)

        # GPS 데이터 표시 프레임
        data_frame = ttk.LabelFrame(self.root, text="GPS 데이터", padding="5")
        data_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # GPS 상태
        ttk.Label(data_frame, text="GPS 상태:").grid(row=0, column=0, padx=5, pady=5)
        self.gps_status_var = tk.StringVar(value="신호 없음")
        ttk.Label(data_frame, textvariable=self.gps_status_var).grid(
            row=0, column=1, padx=5, pady=5
        )

        # 위도
        ttk.Label(data_frame, text="위도:").grid(row=1, column=0, padx=5, pady=5)
        self.lat_var = tk.StringVar(value="N/A")
        ttk.Label(data_frame, textvariable=self.lat_var).grid(
            row=1, column=1, padx=5, pady=5
        )

        # 경도
        ttk.Label(data_frame, text="경도:").grid(row=2, column=0, padx=5, pady=5)
        self.lon_var = tk.StringVar(value="N/A")
        ttk.Label(data_frame, textvariable=self.lon_var).grid(
            row=2, column=1, padx=5, pady=5
        )

        # 속도
        ttk.Label(data_frame, text="속도 (km/h):").grid(row=3, column=0, padx=5, pady=5)
        self.speed_var = tk.StringVar(value="N/A")
        ttk.Label(data_frame, textvariable=self.speed_var).grid(
            row=3, column=1, padx=5, pady=5
        )

        # 시간
        ttk.Label(data_frame, text="시간:").grid(row=4, column=0, padx=5, pady=5)
        self.time_var = tk.StringVar(value="N/A")
        ttk.Label(data_frame, textvariable=self.time_var).grid(
            row=4, column=1, padx=5, pady=5
        )

        # 위성 수
        ttk.Label(data_frame, text="위성 수:").grid(row=5, column=0, padx=5, pady=5)
        self.sat_count_var = tk.StringVar(value="0")
        ttk.Label(data_frame, textvariable=self.sat_count_var).grid(
            row=5, column=1, padx=5, pady=5
        )

        # 상태 표시
        self.status_var = tk.StringVar(value="연결되지 않음")
        ttk.Label(self.root, textvariable=self.status_var).pack(pady=5)

        # 디버그 메시지 표시 영역
        self.debug_text = tk.Text(self.root, height=5, width=50)
        self.debug_text.pack(pady=5)

    def debug_print(self, message):
        self.debug_text.insert(
            tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n"
        )
        self.debug_text.see(tk.END)

    def toggle_connection(self):
        if not self.is_running:
            port = self.port_var.get()
            if not port:
                messagebox.showerror("오류", "COM 포트를 선택해주세요.")
                return

            try:
                self.serial_port = serial.Serial(port, 9600, timeout=1)
                self.is_running = True
                self.connect_btn.config(text="연결 해제")
                self.status_var.set("연결됨")
                self.debug_print(f"COM 포트 {port} 연결 성공")

                # 데이터 수신 스레드 시작
                self.receive_thread = threading.Thread(target=self.receive_data)
                self.receive_thread.daemon = True
                self.receive_thread.start()

            except Exception as e:
                error_msg = f"연결 실패: {str(e)}"
                messagebox.showerror("오류", error_msg)
                self.debug_print(error_msg)
                self.is_running = False
                self.connect_btn.config(text="연결")
                self.status_var.set("연결 실패")
        else:
            self.is_running = False
            if self.serial_port:
                self.serial_port.close()
            self.connect_btn.config(text="연결")
            self.status_var.set("연결 해제됨")
            self.debug_print("연결 해제됨")

    def receive_data(self):
        while self.is_running:
            try:
                if self.serial_port.in_waiting:
                    line = (
                        self.serial_port.readline()
                        .decode("ascii", errors="replace")
                        .strip()
                    )
                    self.debug_print(f"수신: {line[:50]}...")  # 긴 데이터는 일부만 표시

                    try:
                        msg = pynmea2.parse(line)

                        if isinstance(msg, pynmea2.RMC):
                            # RMC 메시지 처리
                            if msg.status == "A":  # 유효한 데이터인 경우
                                self.gps_status_var.set("정상")
                                if msg.latitude and msg.longitude:
                                    self.lat_var.set(f"{msg.latitude:.6f}°")
                                    self.lon_var.set(f"{msg.longitude:.6f}°")

                                    # 속도 업데이트 (노트 -> km/h)
                                    if msg.spd_over_grnd is not None:
                                        speed_kmh = msg.spd_over_grnd * 1.852
                                        self.speed_var.set(f"{speed_kmh:.2f}")

                                    # 시간 업데이트
                                    if msg.timestamp:
                                        self.time_var.set(
                                            msg.timestamp.strftime("%H:%M:%S")
                                        )
                            else:
                                self.gps_status_var.set("신호 없음")
                                self.lat_var.set("N/A")
                                self.lon_var.set("N/A")
                                self.speed_var.set("N/A")

                        elif isinstance(msg, pynmea2.GGA):
                            # GGA 메시지 처리
                            if msg.gps_qual > 0:  # GPS 품질이 0보다 큰 경우
                                self.sat_count_var.set(str(msg.num_sats))
                            else:
                                self.sat_count_var.set("0")

                    except pynmea2.ParseError as e:
                        self.debug_print(f"NMEA 파싱 오류: {str(e)}")

            except serial.SerialException as e:
                error_msg = f"시리얼 통신 오류: {str(e)}"
                self.debug_print(error_msg)
                self.is_running = False
                self.status_var.set("통신 오류")
                break
            except Exception as e:
                error_msg = f"데이터 수신 오류: {str(e)}"
                self.debug_print(error_msg)
                self.is_running = False
                self.status_var.set("데이터 수신 오류")
                break


if __name__ == "__main__":
    root = tk.Tk()
    app = GPSGUI(root)
    root.mainloop()
