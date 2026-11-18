#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import requests

CONFIG_DIR = "config_abas"
STATE_FILE = "abas_abertas.json"
VERSAO = "2.2.3"
AUTOR = "Elielson Silva"
TAMANHO_JANELA = "430x510"
MAX_RELES = 8

os.makedirs(CONFIG_DIR, exist_ok=True)

def carregar_json(caminho, padrao):
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao

def salvar_json(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

class DragDropNotebook(ttk.Notebook):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._drag_start_index = None
        self.bind("<ButtonPress-1>", self.on_button_press)
        self.bind("<B1-Motion>", self.on_button_motion)
        self.bind("<ButtonRelease-1>", self.on_button_release)

    def on_button_press(self, event):
        elem = self.identify(event.x, event.y)
        if "label" in elem:
            self._drag_start_index = self.index(f"@{event.x},{event.y}")

    def on_button_motion(self, event):
        if self._drag_start_index is None:
            return
        try:
            cur_index = self.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return

        if cur_index != self._drag_start_index and cur_index < self.index("end") - 1:
            tab_id = self.tabs()[self._drag_start_index]
            self.insert(cur_index, tab_id)
            self._drag_start_index = cur_index

    def on_button_release(self, event):
        if hasattr(self.master, "salvar_abas_abertas"):
            self.master.salvar_abas_abertas()
        self._drag_start_index = None

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Controle de Réles - {AUTOR} - v{VERSAO}")
        self.geometry(TAMANHO_JANELA)

        self.tabs = DragDropNotebook(self)
        self.tabs.pack(expand=1, fill="both")

        self.abas = {}  # {titulo: (frame, AbaRele)}
        self.tabs.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.adicionar_botao_nova_aba()
        self.restaurar_abas()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.after(100, self.selecionar_primeira_aba)

    def on_tab_changed(self, event):
        current = self.tabs.index("current")
        if current == self.tabs.index("end") - 1:
            self.adicionar_aba()
            self.tabs.select(self.tabs.index("end") - 2)

    def adicionar_botao_nova_aba(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text=" + ")

    def adicionar_aba(self, config=None):
        frame = ttk.Frame(self.tabs)
        titulo = config["titulo"] if config else f"Aba {len(self.abas) + 1}"
        nome_arquivo = f"{titulo.replace(' ', '_')}.json"
        caminho_config = os.path.join(CONFIG_DIR, nome_arquivo)

        if not config:
            config = {
                "titulo": titulo,
                "ip": "",
                "num_reles": 8,
                "nomes_reles": [f"Relé {i+1}" for i in range(8)],
                "cor_fundo": "#ffffff",
                "cor_botoes": "#cccccc",
            }
            salvar_json(caminho_config, config)

        conteudo = AbaRele(frame, config, caminho_config, self)
        conteudo.pack(expand=1, fill="both")

        self.abas[titulo] = (frame, conteudo)
        self.tabs.insert(self.tabs.index("end") - 1, frame, text=titulo)
        self.salvar_abas_abertas()
        self.tabs.select(frame)

    def remover_aba(self, titulo):
        if titulo in self.abas:
            if messagebox.askyesno("Confirmar", f"Deseja excluir a aba '{titulo}' e sua configuração?"):
                frame, _ = self.abas[titulo]
                self.tabs.forget(frame)
                del self.abas[titulo]
                caminho = os.path.join(CONFIG_DIR, f"{titulo.replace(' ', '_')}.json")
                if os.path.exists(caminho):
                    os.remove(caminho)
                self.salvar_abas_abertas()

    def atualizar_titulo_aba(self, antigo_titulo, novo_titulo, novo_caminho):
        if antigo_titulo in self.abas:
            frame, conteudo = self.abas.pop(antigo_titulo)
            self.abas[novo_titulo] = (frame, conteudo)
            index = self.tabs.index(frame)
            self.tabs.tab(index, text=novo_titulo)
            conteudo.caminho = novo_caminho
            self.salvar_abas_abertas()

    def salvar_abas_abertas(self):
        titulos = []
        for i in range(self.tabs.index("end") - 1):
            tab_id = self.tabs.tabs()[i]
            titulo = self.tabs.tab(tab_id, "text")
            titulos.append(titulo)
        salvar_json(STATE_FILE, titulos)

    def restaurar_abas(self):
        abas = carregar_json(STATE_FILE, [])
        if not abas:
            self.adicionar_aba()
        else:
            for titulo in abas:
                caminho = os.path.join(CONFIG_DIR, f"{titulo.replace(' ', '_')}.json")
                config = carregar_json(caminho, None)
                if config:
                    self.adicionar_aba(config)

    def on_close(self):
        self.salvar_abas_abertas()
        self.destroy()

    def selecionar_primeira_aba(self):
        if self.tabs.index("end") > 1:
            self.tabs.select(0)

class AbaRele(tk.Frame):
    def __init__(self, parent, config, caminho_config, app):
        super().__init__(parent, bg=config["cor_fundo"])
        self.config = config
        self.caminho = caminho_config
        self.app = app
        self.status_ip = tk.StringVar()
        self.criar_interface()
        self.verificar_conectividade()

    def criar_interface(self):
        tk.Label(
            self,
            text=self.config["titulo"],
            bg=self.config["cor_fundo"],
            font=("Arial", 18, "bold"),
        ).pack(pady=5)

        self.label_status = tk.Label(
            self,
            textvariable=self.status_ip,
            bg=self.config["cor_fundo"],
            font=("Arial", 10),
        )
        self.label_status.pack()

        frame_reles = tk.Frame(self, bg=self.config["cor_fundo"])
        frame_reles.pack(expand=1, fill="both", pady=10)

        frame_esq = tk.Frame(frame_reles, bg=self.config["cor_fundo"])
        frame_esq.pack(side="left", expand=1, fill="both", padx=5)

        frame_dir = tk.Frame(frame_reles, bg=self.config["cor_fundo"])
        frame_dir.pack(side="right", expand=1, fill="both", padx=5)

        for i in range(self.config["num_reles"]):
            nome = (
                self.config["nomes_reles"][i]
                if i < len(self.config["nomes_reles"])
                else f"Relé {i+1}"
            )
            btn = tk.Button(
                frame_esq if i < 4 else frame_dir,
                text=nome,
                bg=self.config["cor_botoes"],
                width=18,
                height=4,
                wraplength=120,
                justify="center",
                command=lambda i=i: self.acionar_rele(i + 1),
            )
            btn.pack(pady=3, fill="x")

        frame_botoes = tk.Frame(self, bg=self.config["cor_fundo"])
        frame_botoes.pack(pady=10)

        tk.Button(frame_botoes, text="Configurar", command=self.abrir_configuracoes).pack(
            side="left", padx=5
        )
        tk.Button(frame_botoes, text="Fechar Aba", command=self.fechar_aba).pack(
            side="left", padx=5
        )

        tk.Label(
            self,
            text=f"Criado por: {AUTOR}",
            bg=self.config["cor_fundo"],
            font=("Arial", 9),
        ).pack(side="bottom", pady=10)

    def acionar_rele(self, numero):
        try:
            url = f"http://{self.config['ip']}/{numero}1:teste"
            requests.get(url, timeout=2)
            self.mostrar_mensagem_temporaria(f"Relé {numero} acionado com sucesso!", 2000)
        except requests.exceptions.ConnectionError as e:
            if "BadStatusLine" in str(e) or "Connection aborted" in str(e):
                self.mostrar_mensagem_temporaria(f"Relé {numero} foi acionado", 2000)
            else:
                messagebox.showerror("Erro de conexão", f"Erro ao conectar: {e}")
        except Exception as e:
            messagebox.showerror("Erro inesperado", f"Ocorreu um erro: {e}")

    def mostrar_mensagem_temporaria(self, mensagem, tempo_ms=2000):
        janela_msg = tk.Toplevel(self)
        janela_msg.title("Mensagem")
        janela_msg.geometry("300x100")
        janela_msg.resizable(False, False)
        janela_msg.attributes("-topmost", True)

        label = tk.Label(janela_msg, text=mensagem, font=("Arial", 12))
        label.pack(expand=True, fill="both", padx=10, pady=10)

        self.center_window(janela_msg, 300, 100)

        janela_msg.after(tempo_ms, janela_msg.destroy)

    def center_window(self, janela, width, height):
        x = self.winfo_rootx() + self.winfo_width() // 2 - width // 2
        y = self.winfo_rooty() + self.winfo_height() // 2 - height // 2
        janela.geometry(f"{width}x{height}+{x}+{y}")

    def abrir_configuracoes(self):
        janela = tk.Toplevel(self)
        janela.title(f"Configurar aba: {self.config['titulo']}")
        janela.geometry("350x580")
        janela.resizable(False, False)

        tk.Label(janela, text="Título da Aba:").pack(pady=5)
        titulo_entry = tk.Entry(janela)
        titulo_entry.insert(0, self.config["titulo"])
        titulo_entry.pack(pady=5, fill="x", padx=10)

        tk.Label(janela, text="IP do servidor:").pack(pady=5)
        ip_entry = tk.Entry(janela)
        ip_entry.insert(0, self.config["ip"])
        ip_entry.pack(pady=5, fill="x", padx=10)

        tk.Label(janela, text="Número de relés (1 a 8):").pack(pady=5)
        reles_spin = tk.Spinbox(janela, from_=1, to=MAX_RELES)
        reles_spin.delete(0, "end")
        reles_spin.insert(0, self.config["num_reles"])
        reles_spin.pack(pady=5, fill="x", padx=10)

        tk.Label(janela, text="Nomes dos relés:").pack(pady=5)
        nomes_entries = []
        for i in range(MAX_RELES):
            entry = tk.Entry(janela)
            entry.pack(pady=2, fill="x", padx=10)
            nome = (
                self.config["nomes_reles"][i]
                if i < len(self.config["nomes_reles"])
                else f"Relé {i+1}"
            )
            entry.insert(0, nome)
            nomes_entries.append(entry)

        tk.Label(janela, text="Cor de fundo:").pack(pady=5)
        btn_cor_fundo = tk.Button(
            janela,
            bg=self.config["cor_fundo"],
            width=10,
            command=lambda: self.selecionar_cor(btn_cor_fundo, "cor_fundo"),
        )
        btn_cor_fundo.pack()

        tk.Label(janela, text="Cor dos botões:").pack(pady=5)
        btn_cor_botoes = tk.Button(
            janela,
            bg=self.config["cor_botoes"],
            width=10,
            command=lambda: self.selecionar_cor(btn_cor_botoes, "cor_botoes"),
        )
        btn_cor_botoes.pack()

        def salvar():
            novo_titulo = titulo_entry.get().strip()
            if not novo_titulo:
                messagebox.showerror("Erro", "Título não pode ser vazio.")
                return

            antigo_titulo = self.config["titulo"]
            novo_nome_arquivo = f"{novo_titulo.replace(' ', '_')}.json"
            novo_caminho = os.path.join(CONFIG_DIR, novo_nome_arquivo)

            # Se o título mudou e o arquivo com novo nome já existe
            if novo_titulo != antigo_titulo and os.path.exists(novo_caminho):
                usar_existente = messagebox.askyesno(
                    "Arquivo Existente",
                    f"Já existe uma aba com o nome '{novo_titulo}'.\n"
                    "Deseja carregar a configuração existente e descartar alterações atuais?"
                )
                if usar_existente:
                    config_existente = carregar_json(novo_caminho, None)
                    if not config_existente:
                        messagebox.showerror(
                            "Erro",
                            "Não foi possível carregar o arquivo de configuração existente."
                        )
                        return

                    # Atualiza o arquivo config e caminho
                    self.config = config_existente
                    self.caminho = novo_caminho

                    # Atualiza o título visível dentro da aba
                    # Primeiro, atualiza Label do título (assumindo que é o primeiro widget)
                    for widget in self.winfo_children():
                        if isinstance(widget, tk.Label) and widget.cget("font") == ("Arial", 18, "bold"):
                            widget.config(text=novo_titulo)
                            break

                    # Atualiza o título da aba no notebook e no dicionário de abas do app
                    if antigo_titulo in self.app.abas:
                        frame, _ = self.app.abas.pop(antigo_titulo)
                        index = self.app.tabs.index(frame)
                        self.app.tabs.tab(index, text=novo_titulo)
                        self.app.abas[novo_titulo] = (frame, self)

                    salvar_json(self.caminho, self.config)

                    janela.destroy()
                    self.reiniciar_aba()
                else:
                    # Usuário não quer usar existente, deixa janela aberta
                    return

            else:
                # Título não mudou para um existente (ou é mesmo nome)
                # Se mudou, renomeia arquivo
                if novo_titulo != antigo_titulo:
                    try:
                        os.rename(self.caminho, novo_caminho)
                        self.caminho = novo_caminho

                        # Atualiza título da aba no notebook e no dicionário
                        if antigo_titulo in self.app.abas:
                            frame, _ = self.app.abas.pop(antigo_titulo)
                            index = self.app.tabs.index(frame)
                            self.app.tabs.tab(index, text=novo_titulo)
                            self.app.abas[novo_titulo] = (frame, self)

                        # Atualiza Label do título na aba
                        for widget in self.winfo_children():
                            if isinstance(widget, tk.Label) and widget.cget("font") == ("Arial", 18, "bold"):
                                widget.config(text=novo_titulo)
                                break

                    except Exception as e:
                        messagebox.showerror("Erro", f"Erro ao renomear arquivo: {e}")
                        return

                self.config["titulo"] = novo_titulo
                self.config["ip"] = ip_entry.get().strip()
                self.config["num_reles"] = int(reles_spin.get())
                self.config["nomes_reles"] = [e.get() for e in nomes_entries][
                    : self.config["num_reles"]
                ]
                salvar_json(self.caminho, self.config)

                janela.destroy()
                self.reiniciar_aba()

        tk.Button(janela, text="Salvar", command=salvar).pack(pady=10)

    def selecionar_cor(self, botao, atributo):
        cor = colorchooser.askcolor()[1]
        if cor:
            self.config[atributo] = cor
            botao.config(bg=cor)

    def reiniciar_aba(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.configure(bg=self.config["cor_fundo"])
        self.criar_interface()

    def fechar_aba(self):
        titulo = self.config["titulo"]
        if messagebox.askyesno(
            "Confirmar",
            f"Deseja realmente fechar a aba '{titulo}'? Isso excluirá seu arquivo de configuração.",
        ):
            self.app.remover_aba(titulo)

    def verificar_conectividade(self):
        ip = self.config["ip"]
        if not ip:
            self.status_ip.set("IP não configurado")
            self.label_status.config(fg="black")
            self.after(5000, self.verificar_conectividade)
            return

        try:
            url = f"http://{ip}/"
            r = requests.get(url, timeout=2)
            if r.ok:
                self.status_ip.set("Status: Online")
                self.label_status.config(fg="darkgreen")
            else:
                self.status_ip.set("Status: Offline")
                self.label_status.config(fg="red")
        except Exception:
            self.status_ip.set("Status: Offline")
            self.label_status.config(fg="red")

        self.after(5000, self.verificar_conectividade)

if __name__ == "__main__":
    app = App()
    app.mainloop()
