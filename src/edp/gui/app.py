"""GUI (View/Controller) do edp.

Regra de ouro: a GUI NAO contem logica de patch. Ela apenas coleta entrada,
chama o ``EsrService`` (Core ja testado) e exibe resultados/progresso.
O trabalho roda em uma thread separada para nao travar a interface.

O botao de patch gera diretamente o disco de boot direto (ESR + FreeDVDBoot),
usando os payloads/loader embutidos no pacote. Nao ha nada para o usuario
configurar.
"""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..domain.errors import EsrError
from ..domain.models import IsoAnalysis
from ..patcher.service import EsrService
from ..paths import default_output_path

_POLL_MS = 80
# Sufixo do arquivo de saida sugerido: o botao gera ESR + FreeDVDBoot.
_OUTPUT_SUFFIX = "fdvdb"
_ICON_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "icons",
)
_ICON_PNG = os.path.join(_ICON_DIR, "edp_128.png")
# Formato nativo do Windows (barra de tarefas/Explorer); ausente nos demais SOs.
_ICON_ICO = os.path.join(_ICON_DIR, "edp.ico")


class EdpApp(tk.Tk):
    def __init__(self, service=None):
        super().__init__()
        self.service = service or EsrService()
        self._queue = queue.Queue()
        self._busy = False

        self.title("EDP — ESR Disc Patcher")
        self._apply_icon()
        self._build_widgets()
        self._fix_size()
        self.after(_POLL_MS, self._poll_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_icon(self):
        """Define o icone da janela (barra de titulo/taskbar), por SO.

        Windows usa o ``.ico`` via ``iconbitmap`` (formato nativo da barra de
        tarefas/Explorer); macOS/Linux usam o PNG via ``iconphoto``. Cada passo
        e tolerante a falha: o icone e cosmetico e nunca deve impedir a GUI de
        abrir (ex.: asset ausente num empacotamento minimo).
        """
        self._icon_image = None
        if os.name == "nt" and os.path.exists(_ICON_ICO):
            try:
                self.iconbitmap(_ICON_ICO)
                return
            except Exception:  # pragma: no cover - icone e cosmetico
                pass  # cai para o PNG abaixo
        try:
            self._icon_image = tk.PhotoImage(file=_ICON_PNG)
            self.iconphoto(True, self._icon_image)
        except Exception:  # pragma: no cover - icone e cosmetico
            self._icon_image = None

    # -- construcao da UI ---------------------------------------------------
    def _build_widgets(self):
        pad = {"padx": 8, "pady": 4}
        self._pad = pad

        # Selecao de arquivo
        file_frame = ttk.LabelFrame(self, text="")
        file_frame.pack(fill="x", **pad)
        ttk.Label(file_frame, text="Arquivo de entrada:").grid(
            row=0, column=0, sticky="e", padx=6, pady=6
        )
        self.input_var = tk.StringVar()
        self._input_entry = ttk.Entry(file_frame, textvariable=self.input_var)
        self._input_entry.grid(row=0, column=1, sticky="ew", padx=6, pady=6)
        self._input_entry.bind("<Return>", lambda _e: self._analyze())
        self._choose_input_button = ttk.Button(
            file_frame, text="Selecionar...", command=self._choose_input
        )
        self._choose_input_button.grid(row=0, column=2, padx=6, pady=6)
        file_frame.columnconfigure(1, weight=1)

        # Diagnostico
        info_frame = ttk.LabelFrame(self, text="")
        info_frame.pack(fill="both", expand=True, **pad)
        self.info_text = tk.Text(info_frame, height=10, wrap="word", state="disabled")
        self.info_text.pack(fill="both", expand=True, padx=6, pady=6)

        # Saida (mesmo layout do campo de entrada: LabelFrame com borda, sem titulo)
        out_frame = ttk.LabelFrame(self, text="")
        out_frame.pack(fill="x", **pad)
        self.output_var = tk.StringVar()
        ttk.Label(out_frame, text="Arquivo de sa\u00edda:").grid(
            row=0, column=0, sticky="e", padx=6, pady=6
        )
        self._output_entry = ttk.Entry(out_frame, textvariable=self.output_var)
        self._output_entry.grid(row=0, column=1, sticky="ew", padx=6, pady=6)
        self._choose_output_button = ttk.Button(
            out_frame, text="Salvar como...", command=self._choose_output
        )
        self._choose_output_button.grid(row=0, column=2, padx=6, pady=6)
        out_frame.columnconfigure(1, weight=1)

        # Acoes
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", **pad)
        self.patch_button = ttk.Button(action_frame, text="Aplicar patch", command=self._patch)
        self.patch_button.pack(fill="x", padx=6)

        # Progresso (oculto ate acionar o patch)
        self.progress_frame = ttk.Frame(self)
        self.progress = ttk.Progressbar(
            self.progress_frame, mode="determinate", maximum=100
        )
        self.progress.pack(fill="x", padx=6)
        self.status_var = tk.StringVar(value="")
        ttk.Label(self.progress_frame, textvariable=self.status_var).pack(
            anchor="w", padx=6, pady=2
        )

        self._render_placeholder()

    def _fix_size(self):
        """Trava a janela no tamanho que abre (nao redimensionavel)."""
        # Mede com o loader visivel para reservar espaco quando ele aparecer.
        self.progress_frame.pack(fill="x", **self._pad)
        self.update_idletasks()
        width = max(self.winfo_reqwidth(), 640)
        height = self.winfo_reqheight()
        self.geometry("%dx%d" % (width, height))
        self.resizable(False, False)
        self.progress_frame.pack_forget()

    # -- helpers de UI ------------------------------------------------------
    def _render_placeholder(self):
        self._set_info("Selecione uma imagem de disco (.iso) para come\u00e7ar.")

    def _set_info(self, text):
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", text)
        self.info_text.configure(state="disabled")

    def _render_analysis(self, analysis: IsoAnalysis):
        src = self.input_var.get().strip()
        lines = [
            "Arquivo:          %s" % (os.path.basename(src) or "-"),
            "Caminho:          %s" % (src or "-"),
            "Tamanho:          %d bytes (%.1f MiB)" % (analysis.size, analysis.size / 1048576),
            "UDF:              %s" % (
                "sim (%s @ setor %d)" % (analysis.udf.standard, analysis.udf.sector)
                if analysis.is_udf else "nao"
            ),
            "Estado:           %s" % analysis.patch_state,
            "Volume ID:        %s" % (analysis.volume_id or "-"),
            "Game ID:          %s" % (analysis.game_id or "-"),
            "Regiao:           %s" % (analysis.region or "-"),
            "Boot executable:  %s" % (analysis.boot_executable or "-"),
        ]
        if analysis.elf is not None:
            lines.append(
                "ELF:              32-bit=%s LE=%s MIPS=%s entry=0x%X"
                % (analysis.elf.is_32bit, analysis.elf.is_little_endian,
                   analysis.elf.is_mips, analysis.elf.entry)
            )
        for problem in analysis.elf_problems:
            lines.append("  ! ELF: %s" % problem)
        for warning in analysis.warnings:
            lines.append("  ! %s" % warning)
        self._set_info("\n".join(lines))

    def _set_busy(self, busy, status=None):
        """Trava/destrava TODA a entrada durante o trabalho (nao so o patch).

        Sem isto, Enter no campo ou os botoes de selecao poderiam disparar uma
        segunda analise concorrente enquanto outra operacao ja roda na thread.
        """
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.patch_button.configure(state=state)
        self._input_entry.configure(state=state)
        self._output_entry.configure(state=state)
        self._choose_input_button.configure(state=state)
        self._choose_output_button.configure(state=state)
        if status:
            self.status_var.set(status)

    def _show_loader(self):
        """Mostra a barra de progresso + status (so aparece ao acionar o patch)."""
        if not self.progress_frame.winfo_manager():
            self.progress_frame.pack(fill="x", **self._pad)

    # -- acoes --------------------------------------------------------------
    def _choose_input(self):
        if self._busy:
            return
        path = filedialog.askopenfilename(
            title="Selecione a imagem de disco",
            filetypes=[("Imagem ISO", "*.iso"), ("Todos os arquivos", "*.*")],
        )
        if not path:
            return
        self.input_var.set(path)
        self.output_var.set(default_output_path(path, _OUTPUT_SUFFIX))
        self._analyze()

    def _choose_output(self):
        if self._busy:
            return
        path = filedialog.asksaveasfilename(
            title="Salvar ISO de saida",
            defaultextension=".iso",
            filetypes=[("Imagem ISO", "*.iso"), ("Todos os arquivos", "*.*")],
        )
        if path:
            self.output_var.set(path)

    def _analyze(self):
        if self._busy:
            return
        src = self.input_var.get().strip()
        if not src:
            messagebox.showwarning("edp", "Selecione uma imagem de entrada.")
            return

        def job():
            return self.service.analyze(src)

        self._set_busy(True, "Carregando...")
        threading.Thread(target=self._worker, args=(job, "analyze"), daemon=True).start()

    def _patch(self):
        if self._busy:
            return
        src = self.input_var.get().strip()
        if not src:
            messagebox.showwarning("edp", "Selecione uma imagem de entrada.")
            return
        dst = self.output_var.get().strip()
        if not dst:
            messagebox.showwarning("edp", "Informe o arquivo de saida.")
            return
        # Origem == destino (inclusive em FS case-insensitive/APFS) e barrado
        # pelo core em _validate_paths (samefile), antes de qualquer copia.
        if os.path.exists(dst) and not messagebox.askyesno(
            "edp", "O arquivo de saida ja existe. Sobrescrever?"
        ):
            return

        def job():
            # Sempre gera o disco de boot direto, com os payloads embutidos.
            return self.service.make_fdvdb_image(
                src, dst, progress=self._progress, overwrite=True
            )

        self._show_loader()
        self._set_busy(True, "Gerando disco...")
        self.progress.configure(value=0)
        threading.Thread(target=self._worker, args=(job, "patch"), daemon=True).start()

    # -- threading / progresso ---------------------------------------------
    def _progress(self, done, total):
        self._queue.put(("progress", (done, total)))

    def _worker(self, job, tag):
        try:
            result = job()
        except EsrError as exc:
            self._queue.put(("error", str(exc)))
        except Exception as exc:  # pragma: no cover - defensivo
            self._queue.put(("error", "erro inesperado: %s" % exc))
        else:
            self._queue.put(("done", (tag, result)))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                try:
                    self._handle_message(kind, payload)
                except Exception as exc:  # pragma: no cover - defensivo
                    # Nunca deixar a fila travar a UI: destrava e avisa.
                    self._set_busy(False, "Erro.")
                    messagebox.showerror(
                        "edp", "erro inesperado na interface: %s" % exc
                    )
        except queue.Empty:
            pass
        finally:
            # Reagenda mesmo apos um erro, para a UI nao congelar em "ocupado".
            self.after(_POLL_MS, self._poll_queue)

    def _handle_message(self, kind, payload):
        if kind == "progress":
            done, total = payload
            if total > 0:
                self.progress.configure(value=int(done * 100 / total))
                self.status_var.set("Gravando... %d%%" % int(done * 100 / total))
        elif kind == "error":
            self._set_busy(False, "Erro.")
            messagebox.showerror("edp", payload)
        elif kind == "done":
            tag, result = payload
            if tag == "analyze":
                self._set_busy(False, "Pronto.")
                try:
                    self._render_analysis(result)
                except Exception as exc:  # pragma: no cover - defensivo
                    self._set_info("Falha ao exibir o diagnostico: %s" % exc)
                    self.status_var.set("Erro ao exibir diagnostico.")
            else:
                self._set_busy(False, "Concluido.")
                self.progress.configure(value=100)
                report = result
                messagebox.showinfo(
                    "edp",
                    "Disco gerado com sucesso:\n%s" % (report.image_path or "-"),
                )
                # reanalisa a saida gerada
                target = report.image_path or self.input_var.get().strip()
                self.input_var.set(target)
                self.output_var.set(default_output_path(target, _OUTPUT_SUFFIX))
                self._analyze()

    def _on_close(self):
        """Confirma a saida enquanto ha trabalho (evita arquivo de saida parcial)."""
        if self._busy and not messagebox.askyesno(
            "edp",
            "Ha uma operacao em andamento. Sair mesmo assim?\n"
            "O arquivo de saida pode ficar incompleto.",
        ):
            return
        self.destroy()


def main():
    app = EdpApp()
    app.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
