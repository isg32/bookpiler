# Sapan Gajjar 12-07-2025 / 13-07-2025 Report

Basic Logic Of Program 
- Takes Input from ./Data folder
- Merges [Class <class> - <subject> - <Chaptername>] - Questions/Explaination.pdf into one (As Pair)
- Scrapes First line of each pair
- makes index of Chapter <Num> and based on num sorts the pdfs - then merges into one
- Appends index.png from ./assets and pastes it to start of page

Limitations
- EOF File is undefined
- Watermark cannot be added from python
- Cannot Change Formatting of Chapter Name/ NO. as parsing the file will cause Missing data and Corrupted / missing images
- Borders need to be defined 10px away from actual data to make sure that nothing overflows

## File Structure 
```
data
| - Class 3rd English 2025
| | - Class 3rd - English - Adjectives - Explanations.pdf
| | - Class 3rd - English - Adjectives - Questions.pdf
| - Class 3rd Maths 2025
| | - Class 3rd - Maths - Algebra - Explanations.pdf
| | - Class 3rd - Maths - Algebra - Questions.pdf
```
## Naming Structure
```
DIR: [ Class <class> <subject> <year> ]
FILE: [ Class <class> - <subject> - <Chaptername> - <Questions/Explanations>.pdf ]
```