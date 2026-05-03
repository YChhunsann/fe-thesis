# fe-thesis-bachelor

### 1. Install latex compiler
```bash
sudo apt update
sudo apt install texlive-full
```

### 2. Compile latex
```
xelatex thesis.tex
```

### 3. Update your setting json file
```
please using settings.json
```

### 4. Add vertical gap between two line using **\\[0.4em]**
```
\begin{minipage}{0.7\textwidth}
        \raggedright
        {\khmerfont\fontsize{16pt}{20pt}\selectfont សាកលវិទ្យាល័យភូមិន្ទភ្នំពេញ\\[0.6em]}
        {\large\bfseries ROYAL UNIVERSITY OF PHNOM PENH}
\end{minipage}
```

### 5. List down font installed
```
fc-list :lang=km
```

### 6. auto re-render
```
latexmk -xelatex -pvc thesis.tex
```

### 7. How to recomepile
```
latexmk -xelatex thesis.tex
```