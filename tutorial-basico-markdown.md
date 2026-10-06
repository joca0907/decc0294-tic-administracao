# Tutorial Básico de Markdown

Guia exemplificativo para a disciplina DECC0294 - TIC Aplicada à Administração (UFMA).

Markdown é uma linguagem simples para formatar texto. É usada no GitHub, nos roteiros `roteiro-moduloN.md` e neste repositório.

## 1. Títulos

Use `#` no início da linha:

```markdown
# Título 1
## Título 2
### Título 3
```

Resultado:

# Título 1
## Título 2
### Título 3

## 2. Texto básico

```markdown
**negrito** para destaque
*itálico* para ênfase
~~riscado~~ para correção
`código curto` para comandos como `conferir`
```

Resultado: **negrito** para destaque, *itálico* para ênfase, ~~riscado~~ para correção, `código curto` para comandos como `conferir`.

Quebra de linha: deixe uma linha em branco entre parágrafos.

## 3. Listas

Lista não ordenada:

```markdown
- Item 1
- Item 2
  - Subitem 2.1
```

- Item 1
- Item 2
  - Subitem 2.1

Lista ordenada:

```markdown
1. Instalar GitHub Desktop
2. Clonar o repositório
3. Abrir o `index.html`
```

1. Instalar GitHub Desktop
2. Clonar o repositório
3. Abrir o `index.html`

Lista de tarefas (útil em projetos):

```markdown
- [x] Ler roteiro-modulo1.md
- [ ] Executar atividade_modulo1.py
```

- [x] Ler roteiro-modulo1.md
- [ ] Executar atividade_modulo1.py

## 4. Links e imagens

```markdown
[Site da disciplina](https://tadeugomes.github.io/decc0294-tic-administracao/)
![Logotipo UFMA](logo.png)
```

Resultado: [Site da disciplina](https://tadeugomes.github.io/decc0294-tic-administracao/)

## 5. Citações

```markdown
> A quarta revolução industrial muda o trabalho do administrador.
> — Klaus Schwab, 2016
```

> A quarta revolução industrial muda o trabalho do administrador.
> — Klaus Schwab, 2016

## 6. Tabelas

Exemplo com dados da Administração:

```markdown
| Módulo | Tema | Entrega |
|---|---|---|
| 1 | Transformação digital | — |
| 2 | Ambiente digital | A1 |
| 5 | Dados na Administração | A2 |
```

| Módulo | Tema | Entrega |
|---|---|---|
| 1 | Transformação digital | — |
| 2 | Ambiente digital | A1 |
| 5 | Dados na Administração | A2 |

## 7. Blocos de código

Para Python (como nos scripts `atividade_moduloN.py`):

````markdown
```python
print("Olá, Administração!")
```
````

```python
print("Olá, Administração!")
```

## 8. Linha horizontal

Três traços `---` criam uma divisão:

---

## Exercício rápido

1. Crie um arquivo `teste.md`
2. Escreva um título, uma lista e uma tabela
3. Visualize no VS Code com `Ctrl + Shift + V` ou no GitHub

Pronto. Com isso você já lê e escreve 90% dos arquivos `.md` da disciplina.
