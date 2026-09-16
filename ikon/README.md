# OmaAmp-ikonen

Motivet är appens egen signatur: mörkt chassi, fosforgröna spektrumstaplar och en
cyan baslinje. Färgerna är hämtade ur `themes/classic_retro.json`, så ikonen och
fönstret är samma sak.

Reglerna som ikonen följer (de kommer ur vad som faktiskt syns i liststorlek):

* **Hel fyrkant, ingen rundning, ingen skugga, ingen glöd.** Butiken och
  skrivbordsmiljön lägger på sin egen mask; inbakad rundning ger dubbla kanter.
* **Fem breda staplar, inte elva smala.** Siluetten ska gå att läsa i 32 px.
* **Färre färger:** fosforgrönt, en gul topp på mittenstapeln, en nedtonad cyan
  linje. Många små färgaccenter blir gröt.
* **Inga bokstäver.** Text blir oläslig under 128 px.
* **8 bitar per kanal.** Den gamla ikonen var 16 bitar per kanal, vilket ingen av
  de andra apparna använder och som flera bildkedjor hanterar illa.

## Filer

- `omaamp-512.png` — mastern (butiksikon, HiDPI)
- `omaamp-256.png` — standardstorleken i butik och skrivbordsmenyer
- `omaamp-128.png` — minsta butiksstorleken

## Rita om

```sh
python3 ikon/gor-ikonen.py     # kräver Pillow
```

Skriptet ritar i 2048 px och skalar ned med Lanczos, vilket ger mjuka kanter utan
att något behöver kantutjämnas för hand. Ändra `heights` för en annan vågform.
