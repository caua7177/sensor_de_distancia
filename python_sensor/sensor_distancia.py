import serial
import mysql.connector
import time


# Altere 'COM3' para a porta onde seu Arduino está conectado (ex: 'COM4', 'COM5')
portal_serial = 'COM3'  
baud_rate = 9600


db_config = {
    'host': 'localhost',
    'user': 'root',        # Seu usuário do MySQL (padrão é 'root')
    'password': '',        # Sua senha do MySQL (deixe vazio '' se não tiver)
    'database': 'bd_sensor' # Nome do banco de dados que você vai criar
}


try:
    # Inicializa a comunicação com a porta USB e com o Banco de Dados
    arduino = serial.Serial(portal_serial, baud_rate, timeout=1)
    conexao = mysql.connector.connect(**db_config)
    cursor = conexao.cursor()
    
    print("Conectado ao Arduino e ao Banco de Dados! Aguardando dados...")
    time.sleep(2) # Pausa de 2 segundos para estabilizar a conexão serial

    # Loop infinito que fica escutando o Arduino
    while True:
        # Se houver dados chegando na porta serial
        if arduino.in_waiting > 0:
            # Lê a linha enviada pelo Arduino, decodifica de bytes para texto e limpa espaços vazios
            linha = arduino.readline().decode('utf-8').strip()
            
            # Verifica se o dado recebido é realmente um número válido
            if linha.isdigit():
                distancia = int(linha)
                print(f"Distancia capturada: {distancia} cm")
                
                # Prepara o comando SQL para salvar a distância
                comando_sql = "INSERT INTO historico_distancia (valor_cm) VALUES (%s)"
                
                # Executa o comando e envia a alteração de fato para salvar no MySQL
                cursor.execute(comando_sql, (distancia,))
                conexao.commit()

except Exception as e:
    # Se qualquer erro acontecer (cabo desconectado, senha errada, etc), cai aqui
    print(f"Ocorreu um erro no sistema: {e}")

finally:
    # Garante que as conexões serão fechadas com segurança ao encerrar o programa
    if 'cursor' in locals(): 
        cursor.close()
    if 'conexao' in locals(): 
        conexao.close()
    if 'arduino' in locals(): 
        arduino.close()
    print("Conexoes finalizadas com seguranca.")
