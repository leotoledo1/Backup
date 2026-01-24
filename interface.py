import customtkinter as ctk
import threading
import os
import sys

def resource_path(relative_path):
    """ Obtém o caminho absoluto para recursos, funciona em dev e PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def mostrar_loading(funcao_background):
    root = ctk.CTk()
    path_icone = resource_path("merco.ico")
    root.after(200, lambda: root.iconbitmap(path_icone))
    root.title("Mercosistem - Backup")
    root.geometry("350x150")
    root.resizable(False, False)

    # Função para quando o usuário clicar no "X"
    def fechar_janela():
        # Em vez de fechar o programa, apenas esconde a janela
        root.withdraw() 
        # O script continuará rodando em segundo plano até a thread terminar

    root.protocol("WM_DELETE_WINDOW", fechar_janela)

    label = ctk.CTkLabel(root, text="BackupMercosistem em andamento...", font=("Roboto", 14, "bold"))
    label.pack(pady=(25, 10))

    barra = ctk.CTkProgressBar(root, orientation="horizontal", mode="indeterminate", width=280)
    barra.pack(pady=10)
    barra.start()

    # Importante: A thread NÃO pode ser daemon, para o Python não matá-la ao fechar a UI
    t = threading.Thread(target=funcao_background)
    t.daemon = False 
    t.start()

    def checar_thread():
        if t.is_alive():
            root.after(500, checar_thread)
        else:
            # Quando o backup terminar de verdade, encerra o processo
            root.quit() 
            root.destroy()

    checar_thread()
    root.mainloop()