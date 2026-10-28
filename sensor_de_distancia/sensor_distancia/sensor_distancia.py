import math
import random
import tkinter as tk
import serial
import os
import mysql.connector
from dotenv import load_dotenv

caminho_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '.env'))

print(f"Procurando arquivo .env em: {caminho_env}")
caminho_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '.env'))

print(f"Procurando arquivo .env em: {caminho_env}")
load_dotenv(caminho_env)


def obter_conexao():
    try:
        conexao = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )

        if conexao.is_connected():
            print("Conectado ao MySQL!!!")
            return conexao

    except Exception as e:
        print(f"Erro ao conectar o Banco de dados: {e}")

    return None


def criar_tabela(conexao):
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_distancia (
            id INT AUTO_INCREMENT PRIMARY KEY,
            valor_cm INT NOT NULL,
            registrado_em DATETIME NOT NULL
        )
    """)
    conexao.commit()
    cursor.close()





PORTA_SERIAL = 'COM3'   # altere para a porta do seu Arduino
BAUD_RATE = 9600


FUNDO = "#12141A"
DIST_MAX = 200  # distância que enche a barra por completo

# Cada estado: (nome, cor principal, cor do brilho)
FELIZ = ("Tranquilo", "#4ADE80", "#14532D")
NEUTRO = ("Atento", "#FACC15", "#713F12")
SURPRESO = ("Perto!", "#FB923C", "#7C2D12")
ASSUSTADO = ("Muito perto!!", "#F87171", "#7F1D1D")
SEM_DADOS = ("Aguardando...", "#6B7280", "#1F2937")


class Rosto:
    def __init__(self, root, arduino, conexao):
        self.root = root
        self.arduino = arduino
        self.conexao = conexao
        self.cursor = conexao.cursor()
        self.distancia = None
        self.piscando = False
        self.easter = False
        self.frame = 0

        # Atalho pra testar o easter egg: aperta a tecla 6 ou 7
        root.bind("<Key-6>", self.easter_egg)
        root.bind("<Key-7>", self.easter_egg)

        root.title("Sensor")
        root.configure(bg=FUNDO)
        root.resizable(False, False)
        self.c = tk.Canvas(root, width=400, height=480, bg=FUNDO, highlightthickness=0)
        self.c.pack()

        self.desenhar()
        self.ler_serial()
        self.piscar()
        root.protocol("WM_DELETE_WINDOW", self.fechar)

    
    def ler_serial(self):
        try:
            while self.arduino.in_waiting > 0:
                linha = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                if linha.isdigit():
                    self.distancia = int(linha)
                    self.cursor.execute(
                        "INSERT INTO historico_distancia (valor_cm, registrado_em) VALUES (%s, NOW())",
                        (self.distancia,))
                    self.conexao.commit()
                    if self.distancia == 67:
                        self.easter_egg()
                    self.desenhar()
        except Exception as e:
            print(f"Erro: {e}")
        self.root.after(100, self.ler_serial)

    # ---------- PISCAR ----------
    def piscar(self):
        self.piscando = True
        self.desenhar()
        self.root.after(150, self.abrir)

    def abrir(self):
        self.piscando = False
        self.desenhar()
        self.root.after(3500, self.piscar)

    # ---------- ESTADO ----------
    def estado(self):
        d = self.distancia
        if d is None:
            return SEM_DADOS
        if d >= 100:
            return FELIZ
        if d >= 50:
            return NEUTRO
        if d >= 20:
            return SURPRESO
        return ASSUSTADO

    
    def olho(self, x, y, w, h, cor, brilho):
        c = self.c
        # brilho (maior e escuro, fica atrás)
        c.create_oval(x - w - 12, y - h - 12, x + w + 12, y + h + 12, fill=brilho, outline="")
        # olho
        c.create_oval(x - w, y - h, x + w, y + h, fill=cor, outline="")

    def desenhar(self):
        if self.easter:  # durante o easter egg, o rosto fica quieto
            return
        c = self.c
        c.delete("all")
        nome, cor, brilho = self.estado()

        # Olhos: (largura, altura) muda com a expressão
        if self.piscando or nome == "Aguardando...":
            w, h = 32, 4
        elif nome == "Tranquilo":
            w, h = 32, 42
        elif nome == "Atento":
            w, h = 32, 32
        elif nome == "Perto!":
            w, h = 42, 50
        else:
            w, h = 26, 26

        self.olho(120, 170, w, h, cor, brilho)
        self.olho(280, 170, w, h, cor, brilho)

        # Sobrancelhas de preocupação
        if nome == "Muito perto!!" and not self.piscando:
            c.create_line(85, 115, 150, 135, width=7, fill=cor, capstyle="round")
            c.create_line(315, 115, 250, 135, width=7, fill=cor, capstyle="round")

        # Boca
        if nome == "Tranquilo":
            c.create_arc(150, 250, 250, 320, start=200, extent=140,
                         style="arc", width=8, outline=cor)
        elif nome == "Perto!":
            c.create_oval(180, 270, 220, 320, outline=cor, width=7)
        elif nome == "Muito perto!!":
            c.create_line(150, 300, 175, 280, 200, 300, 225, 280, 250, 300,
                          width=8, fill=cor, smooth=True, capstyle="round")
        else:
            c.create_line(160, 290, 240, 290, width=8, fill=cor, capstyle="round")

        # Distância
        texto = "-- cm" if self.distancia is None else f"{self.distancia} cm"
        c.create_text(200, 385, text=texto, fill="white", font=("Segoe UI", 32, "bold"))
        c.create_text(200, 420, text=nome, fill=cor, font=("Segoe UI", 12))

        # Barra de proximidade (mais cheia = mais longe)
        c.create_line(60, 450, 340, 450, width=8, fill="#2A2E38", capstyle="round")
        if self.distancia is not None:
            pct = min(self.distancia, DIST_MAX) / DIST_MAX
            c.create_line(60, 450, 60 + 280 * pct, 450, width=8, fill=cor, capstyle="round")

    # ---------- EASTER EGG: 6 7 ----------
    def easter_egg(self, evento=None):
        if self.easter:  # já está rodando
            return
        self.easter = True
        self.frame = 0
        self.animar_67()

    def animar_67(self):
        c = self.c
        c.delete("all")
        cores = ["#F472B6", "#60A5FA", "#4ADE80", "#FACC15", "#FB923C"]
        cor = cores[(self.frame // 4) % len(cores)]  # troca de cor a cada 4 frames

        # Confete aleatório
        for _ in range(14):
            x = random.randint(0, 400)
            y = random.randint(0, 480)
            c.create_rectangle(x, y, x + 8, y + 8, fill=random.choice(cores), outline="")

        c.create_text(200, 70, text="SIX SEVEN!", fill=cor, font=("Segoe UI", 28, "bold"))

        # Balanço: um sobe enquanto o outro desce
        balanco = 45 * math.sin(self.frame * 0.6)
        c.create_text(120, 230 - balanco, text="6", fill=cor, font=("Segoe UI", 130, "bold"))
        c.create_text(280, 230 + balanco, text="7", fill=cor, font=("Segoe UI", 130, "bold"))

        # "Mãos" balançando no mesmo ritmo
        c.create_oval(92, 385 - balanco - 28, 148, 385 - balanco + 28, fill=cor, outline="")
        c.create_oval(252, 385 + balanco - 28, 308, 385 + balanco + 28, fill=cor, outline="")

        self.frame += 1
        if self.frame < 70:  # 70 frames x 50 ms = 3,5 segundos
            self.root.after(50, self.animar_67)
        else:
            self.easter = False
            self.desenhar()

    # ---------- ENCERRAR ----------
    def fechar(self):
        self.cursor.close()
        self.conexao.close()
        self.arduino.close()
        self.root.destroy()


if __name__ == "__main__":
    try:
        arduino = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=1)
    except Exception as e:
        print(f"Nao foi possivel conectar ao Arduino: {e}")
        raise SystemExit

    conexao = obter_conexao()
    if conexao is None:
        print("Nao foi possivel conectar ao banco de dados.")
        arduino.close()
        raise SystemExit

    criar_tabela(conexao)

    janela = tk.Tk()
    Rosto(janela, arduino, conexao)
    janela.mainloop()









