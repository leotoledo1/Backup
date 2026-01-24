import customtkinter as ctk
import threading
import os
import sys

# =================================================================
# UTILITÁRIOS DE INTERFACE E RECURSOS
# =================================================================

def resource_path(relative_path):
    """ 
    Localiza o caminho dos recursos (como o ícone .ico) dentro do 
    pacote gerado pelo PyInstaller ou no diretório de desenvolvimento.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# =================================================================
# JANELA DE PROGRESSO (LOADING)
# =================================================================

def mostrar_loading(funcao_background):
    """
    Cria uma janela visual com uma barra de progresso indeterminada.
    Gerencia a execução da lógica de backup em uma thread separada para
    não congelar a interface gráfica (GUI).
    """
    # Configuração inicial da janela principal usando CustomTkinter
    root = ctk.CTk()
    
    # Define o ícone da janela (merco.ico deve estar no diretório ou embutido)
    path_icone = resource_path("merco.ico")
    root.after(200, lambda: root.iconbitmap(path_icone))
    
    root.title("Mercosistem - Backup")
    root.geometry("350x150")
    root.resizable(False, False)

    def fechar_janela():
        """ 
        Handler para o botão de fechamento (X).
        A janela é escondida (withdraw), mas o processo continua rodando
        até que a thread de backup finalize com segurança.
        """
        root.withdraw() 

    # Sobrescreve o comportamento do botão fechar padrão do Windows
    root.protocol("WM_DELETE_WINDOW", fechar_janela)

    # Elementos visuais: Label de status e Barra de progresso
    label = ctk.CTkLabel(
        root, 
        text="Backup Mercosistem em andamento...", 
        font=("Roboto", 14, "bold")
    )
    label.pack(pady=(25, 10))

    # Barra de progresso em modo "indeterminate" (fica indo e voltando)
    barra = ctk.CTkProgressBar(root, orientation="horizontal", mode="indeterminate", width=280)
    barra.pack(pady=10)
    barra.start()

    # =================================================================
    # GERENCIAMENTO DE THREADS
    # =================================================================

    # Dispara a função de backup (rodar_backup) em uma thread separada.
    # daemon=False garante que o Python espere o backup terminar antes de fechar.
    t = threading.Thread(target=funcao_background)
    t.daemon = False 
    t.start()

    def checar_thread():
        """
        Função recursiva que monitora se a thread de backup ainda está ativa.
        Se terminou, encerra a interface e fecha o programa completamente.
        """
        if t.is_alive():
            # Verifica novamente após 500ms (0.5 segundos)
            root.after(500, checar_thread)
        else:
            # Finaliza o loop principal da interface
            root.quit() 
            root.destroy()

    # Inicia o monitoramento da thread e o loop da interface
    checar_thread()
    root.mainloop()