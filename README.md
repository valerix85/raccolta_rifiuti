# 🗑️ Raccolta Rifiuti per Home Assistant

Integrazione personalizzata per visualizzare la Raccolta dei rifiuti nel tuo Home Assistant, con supporto ad icone grafiche e visualizzazione in Lovelace.

![HACS Custom](https://img.shields.io/badge/HACS-Custom-blue)
![Platform](https://img.shields.io/badge/Platform-Home%20Assistant-41BDF5)
![Maintainer](https://img.shields.io/badge/Maintainer-DomoticaFacile-blueviolet)
[![Donate](https://img.shields.io/badge/Buy_Me_A_Coffee-%E2%98%95-yellow)](https://www.buymeacoffee.com/domoticafacile)
![GitHub stars](https://img.shields.io/github/stars/DomoticaFacile/raccolta_rifiuti?style=social)
[![Home Assistant installs](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=HA%20installs&suffix=%20users&cacheSeconds=14400&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.raccolta_rifiuti.total)](https://analytics.home-assistant.io/custom_integrations.json)

[![Gruppo Facebook](https://img.shields.io/badge/Gruppo-Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white)](https://www.facebook.com/groups/domoticafacile)
[![Pagina Facebook](https://img.shields.io/badge/Pagina-Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white)](https://www.facebook.com/domoticafacile)
[![YouTube](https://img.shields.io/badge/YouTube-Channel-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/@DomoticaFacile-it)

[![Instagram](https://img.shields.io/badge/Instagram-Profilo-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://www.instagram.com/domoticafacile.it)
[![TikTok](https://img.shields.io/badge/TikTok-Profilo-000000?style=for-the-badge&logo=tiktok&logoColor=white)](https://www.tiktok.com/@domoticafacile)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-Canale-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)](https://whatsapp.com/channel/0029Vb5qW5O4o7qPGrFbRm1T)

**Ti piace questa integrazione?** ⭐ Clicca sulla stella per supportare il progetto!

![image](https://github.com/user-attachments/assets/2647835f-7981-4974-98c8-f82dcfe85b48)

Video Tutorial YouTube: https://www.youtube.com/watch?v=v-wM2uAQTRg
---

## 📦 Funzionalità

✅ Crea il sensore `sensor.raccolta_rifiuti`  
✅ Include attributo `collection_types` (es: `"Plastica", "Carta"`)  
✅ Compatibile con template e card HTML personalizzate  
✅ Supporta immagini per ogni tipo di rifiuto

---

## 🆕 Novità del fork 2.0: giorni a regole, senza calendario

> Fork di [DomoticaFacile/raccolta_rifiuti](https://github.com/DomoticaFacile/raccolta_rifiuti). La modalità YAML originale (calendario) continua a funzionare identica.

**Installazione del fork con HACS:** HACS → ⋮ → Repository personalizzati → `https://github.com/valerix85/raccolta_rifiuti` (tipo *Integrazione*). Se avevi già la versione di DomoticaFacile, rimuovila prima da HACS (stesso dominio `raccolta_rifiuti`); la configurazione YAML resta valida.

Poi da **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Raccolta Rifiuti** imposti i giorni come nel package HassioHelp:

| Sintassi | Significato |
|---|---|
| `lun,ven` | ogni lunedì e venerdì (anche `lunedì`, `mon`, `friday`) |
| `-mar` / `--mar` | martedì delle settimane dispari / pari (numerazione come HassioHelp: la prima settimana di gennaio è pari) |
| `2\|1\|mer` | mercoledì una settimana sì e una no, senza salti a cavallo d'anno (cicli da 2 a 8 settimane, come la versione estesa HassioHelp) |
| `lun#1`, `lun#ult` | primo / ultimo lunedì del mese |
| `25/12` | ogni anno il 25 dicembre |
| `27/12/2026` | una volta sola |

Vengono create (esempio con nome "Raccolta Differenziata"):

- `sensor.raccolta_differenziata_domani` – cosa esporre stasera; ha gli stessi attributi del sensore classico (`collection_types`, `collection_type_codes`) più `message` ("Umido e Carta"), quindi i blueprint funzionano selezionando questo sensore
- `sensor.raccolta_differenziata_oggi`
- `sensor.raccolta_differenziata_prossima_raccolta` – data + `days_remaining`
- un sensore per tipo (es. `sensor.raccolta_differenziata_carta`) con i **giorni mancanti** e le prossime date (`upcoming`)
- `calendar.raccolta_differenziata` – tutte le raccolte nel calendario di HA
- un'entità testo per tipo (es. `text.raccolta_differenziata_giorni_carta`) per **cambiare i giorni direttamente dalla dashboard**

### Eccezioni (festività, scioperi, recuperi)

Facoltativo: scegli un calendario (es. un *Calendario locale* "Eccezioni rifiuti") e crea un evento **nel giorno della raccolta**:

- `No umido` / `Umido annullato` → toglie l'umido quel giorno
- `Raccolta sospesa` / `Nessuna raccolta` → toglie tutto
- `Recupero umido` / `Plastica e vetro` → aggiunge quei tipi

### Card di esempio

```yaml
type: grid
columns: 3
square: false
cards:
  - type: tile
    entity: sensor.raccolta_differenziata_secco_indifferenziata
  - type: tile
    entity: sensor.raccolta_differenziata_umido
  - type: tile
    entity: sensor.raccolta_differenziata_carta
  - type: tile
    entity: sensor.raccolta_differenziata_plastica
  - type: tile
    entity: sensor.raccolta_differenziata_vetro
  - type: tile
    entity: sensor.raccolta_differenziata_verde
```

---

## ⚙️ Installazione tramite HACS

> 💡 Se non hai HACS, segui [questa guida](https://hacs.xyz/docs/setup/download)

1. Vai su **HACS**
2. Cerca "Raccolta Rifiuti" tra le integrazioni e clicca su "Installa"
3. Riavvia Home Assistant

---

## 🧾 Configurazione

Aggiungi nel tuo `configuration.yaml`:

```yaml
sensor:
  - platform: raccolta_rifiuti
    calendar_entity_id: calendar.raccolta_rifiuti
    # language: auto        # opzionale: "auto" (default, segue la lingua di Home Assistant), "it" oppure "en"
    # lookahead_days: 7     # opzionale (default 7): entro quanti giorni cercare la prossima raccolta se oggi non c'è nulla
    # scan_interval: "00:30:00"  # opzionale: intervallo di aggiornamento di sicurezza (default 30 minuti)
    # keywords:                  # opzionale: parole personalizzate scritte nel tuo calendario
    #   multimateriale: [plastic, metal]
    #   sacco viola: plastic
    #   pannolini: pannolini     # un codice nuovo diventa un tipo a sé ("Pannolini")
```

🔄 **Aggiornamento automatico**: oltre all'intervallo, il sensore si aggiorna subito dopo mezzanotte e ogni volta che il calendario cambia stato (es. quando inizia l'evento delle 19:00), quindi non bisogna più aspettare fino a 30 minuti.

⏳ **Calendari lenti (CalDAV, Google...)**: se all'avvio il calendario non è ancora pronto il sensore viene creato comunque, resta *non disponibile* e si popola da solo appena il calendario viene caricato.

🔤 **Riconoscimento**: le parole sono cercate come parole intere, ignorando maiuscole, accenti, punteggiatura ed emoji: `Carta.`, `Carta - Vetro`, `🗑️ Umido`, `Plastica (sacco giallo)`, `PLASTICA E LATTINE` vengono riconosciuti. Codici disponibili per `keywords`: `paper`, `plastic`, `glass`, `organic`, `residual`, `metal`, `green` (oppure un codice nuovo a tua scelta). Gli eventi che non contengono nessuna parola nota compaiono come "Raccolta sconosciuta" e generano un avviso nel log con il testo da aggiungere a `keywords`.

🌍 **Multi-lingua**: puoi scrivere gli eventi del calendario in italiano o in inglese (es. "Carta" o "Paper"), vengono riconosciuti entrambi. L'opzione `language` controlla solo la lingua di *visualizzazione* dello stato e degli attributi del sensore (default: segue la lingua configurata in Home Assistant). È disponibile anche l'attributo `collection_type_codes`, con valori stabili in inglese (es. `"paper"`, `"glass"`), utile per chi vuole scrivere template Lovelace indipendenti dalla lingua.

📅 **Prossima raccolta (`lookahead_days`)**: `state` e `collection_types` continuano a descrivere solo la raccolta di **oggi** (nessuna modifica per chi già usa l'integrazione). In più, se oggi non c'è nulla, il sensore cerca in avanti entro `lookahead_days` giorni e popola:
- `days_remaining`: giorni mancanti alla prossima raccolta trovata (`0` se è oggi)
- `next_collection_date`: data della prossima raccolta (`YYYY-MM-DD`)
- `next_collection_types` / `next_collection_type_codes`: tipi previsti in quella data

Riavvia Home Assistant

---

📆 **Creazione del calendario locale**   (manuale)

Per far funzionare correttamente l'integrazione, è necessario creare manualmente un calendario:

1. Vai su **Impostazioni > Dispositivi e Servizi**
2. Clicca su **Aggiungi Integrazione**
3. Seleziona **"Calendario Locale"**
4. Assegna il nome **`raccolta_rifiuti`** (esattamente così)

5. Inserire nel calendario (il giorno prima della raccolta) i rifiuti che verranno raccolti e l'orario 
quando la card deve mostrare i contenitori (E' possibile inserire: Carta, Plastica, Vetro, Umido, Indifferenziato).

La logica è: se ogni lunedi raccolgono carta e vetro, crea due eventi la domenica,
uno carta e uno vetro, metti orario 19:00 - 23:59 e poi seleziona il lunedi di ogni settimana.
	
---

🧠 Esempio di Template HTML in Lovelace

```yaml
type: conditional
conditions:
  - condition: state
    entity: calendar.raccolta_rifiuti
    state: "on"
card:
  type: markdown
  content: >-
    {% set raccolta = state_attr('sensor.raccolta_rifiuti', 'collection_types') %}

    Domani si raccoglie:

    <div style="display: flex; justify-content: space-evenly; align-items: center;">

    {% if 'Plastica' in raccolta %}
      <img src="/local/images/img_raccolta_rifiuti/plastica.png" style="max-width: 50px; max-height: 50px;" />
    {% endif %}

    {% if 'Carta' in raccolta %}
      <img src="/local/images/img_raccolta_rifiuti/carta.png" style="max-width: 50px; max-height: 50px;" />
    {% endif %}

    {% if 'Vetro' in raccolta %}
      <img src="/local/images/img_raccolta_rifiuti/vetro.png" style="max-width: 50px; max-height: 50px;" />
    {% endif %}

    {% if 'Umido' in raccolta %}
      <img src="/local/images/img_raccolta_rifiuti/umido.png" style="max-width: 50px; max-height: 50px;" />
    {% endif %}

    {% if 'Indifferenziata' in raccolta %}
      <img src="/local/images/img_raccolta_rifiuti/indifferenziata.png" style="max-width: 50px; max-height: 50px;" />
    {% endif %}

    </div>
```

💡 **Versione compatta** (indipendente dalla lingua, mostra anche metallo e verde):

```yaml
type: conditional
conditions:
  - condition: state
    entity: calendar.raccolta_rifiuti
    state: "on"
card:
  type: markdown
  content: >-
    Domani si raccoglie:
    <div style="display:flex;justify-content:space-evenly;align-items:center;">
    {% set img = {'paper':'carta','plastic':'plastica','glass':'vetro','organic':'umido',
                  'residual':'indifferenziata','metal':'metallo','green':'verde'} %}
    {% for c in state_attr('sensor.raccolta_rifiuti','collection_type_codes') or [] %}
      <img src="/local/images/img_raccolta_rifiuti/{{ img.get(c, 'default') }}.png" style="max-width:50px;max-height:50px;" />
    {% endfor %}
    </div>
```

---
🖼️ Immagini (manuale)

Dopo aver completato l'installazione, verifica che sia stata creata la seguente cartella, contenente le immagini:

``` config\www\images\img_raccolta_rifiuti ```

Se la cartella non è presente, puoi crearla manualmente seguendo questi semplici passaggi:

```
Copia la cartella images da:
config\custom_components\raccolta_rifiuti\
a:
config\www\
    
```
Riavvia Home Assistant
---
### 📘 Blueprint (facoltativo ma consigliati)

Per usare i blueprint inclusi:

1. Crea la cartella:
   `config/blueprints/automation/raccolta_rifiuti/`

2. Copia  e incolla nella cartella creata il file YAML che trovi qui:
   [`blueprints/automation/raccolta_rifiuti/`](https://github.com/DomoticaFacile/raccolta_rifiuti/tree/main/blueprints/automation/raccolta_rifiuti)

3. Riavvia Home Assistant o ricarica le automazioni.

Blueprint disponibili:
- `annuncio_raccolta_rifiuti_alexa.yaml` – annuncio con Alexa Media Player
- `annuncio_raccolta_rifiuti_google.yaml` – annuncio su Google/Nest tramite `tts.speak` (qualsiasi motore TTS: Google Translate, Piper, Cloud)
- `notifica_raccolta_rifiuti.yaml` – notifica (app Companion, Telegram, ...) con la variabile `{{ messaggio }}`
- `alexa_start_automation.yaml` – avvio dell'annuncio tramite routine Alexa

In alternativa puoi importarli da **Impostazioni > Automazioni e scenari > Blueprint > Importa blueprint** incollando l'URL del file su GitHub.

👉 Dopo il riavvio, troverai l'automazione disponibile in:
**Impostazioni > Automazioni e Scenari > + Crea automazione**

---
🖼️Screenshots

![image](https://github.com/user-attachments/assets/3b0a8c7b-7e09-4b59-b57e-f7fd8e57a3ae)

![image](https://github.com/user-attachments/assets/bd05df5b-f3ab-4b87-b041-7eba9fef88be)

---

📘 GUIDA DI CONFIGURAZIONE ANNUNCIO VOCALE ALEXA



1️⃣ Creare l’helper (commutatore)

- Vai su: Impostazioni → Dispositivi e servizi → Aiutanti → Crea Aiutante → Commutatore
- Dai al commutatore il seguente nome "Avvia Annuncio Raccolta" (otterrai input_boolean.avvia_annuncio_raccolta)
- Seleziona l'icona "Trash"

2️⃣ Esporre l’helper ad Alexa

Vai su:

- Impostazioni → Assistenti vocali → Esponi
- Cerca "Avvio Annuncio Raccolta"
- Assicurati che il commutatore creato sia esposto ad Alexa

<img width="1155" height="438" alt="image" src="https://github.com/user-attachments/assets/794a6f01-05b9-47d8-8cb9-1be08b78dfaf" />

3️⃣ Crea la routine in Alexa

Apri l'app Amazon Alexa sul tuo smartphone
→ Routine → +

Trigger → Comando vocale
→ "Quali rifiuti devo mettere fuori"
(metti altri trigger a tuo piacimento)

Aggiungi Azione → Casa Intelligente
→ Attiva Avvia Annuncio Raccolta

Salva.

4️⃣ Creare una nuova automazione usando il blueprint "Avvia Annuncio raccolta tramite Alexa"

<img width="1025" height="389" alt="image" src="https://github.com/user-attachments/assets/0ab3005a-73f7-4308-8020-fd371b091282" />


🎉 RISULTATO

Come funziona:

Tu: “Alexa, quali rifiuti devo mettere fuori?”

- Alexa accende il commutatore
- Il blueprint avvia la tua automazione originale
- L’annuncio parte con la tua voce/echo preferito
- Il toggle si spegne automaticamente
  
---

👨‍💻 Sviluppatore

Realizzato con ❤️ da www.domoticafacile.it

Hai suggerimenti o vuoi contribuire?
Apri una issue, una pull request o contattaci tramite i nostri canali social che trovi sul sito.

---

💖 Ringraziamenti:

Un enorme grazie a:

👤 **Bilo2110** – per il prezioso supporto come tester 🧪  
👤 **DaniloGP-91** – per i preziosi suggerimenti nella creazione del blueprint che permette a Google Home di annunciare la raccolta rifiuti 🔊

...e a tutti coloro che supportano e contribuiscono a questo progetto!

Ogni feedback, segnalazione o contributo è sempre benvenuto 😊  
Insieme rendiamo la domotica più facile e divertente!

---

## 📄 Licenza

Questo progetto è distribuito sotto licenza **MIT**.  
Puoi usarlo, modificarlo e distribuirlo liberamente, purché venga mantenuto il copyright originario.

Leggi il file [LICENSE](LICENSE) per i dettagli completi.

---

## ☕ Offrimi un caffè

Se questo progetto ti è stato utile e vuoi supportarmi, puoi offrirmi un caffè cliccando qui sotto! 😊

[![Buy Me A Coffee](https://github.com/appcraftstudio/buymeacoffee/raw/master/Images/snapshot-bmc-button.png)](https://www.buymeacoffee.com/domoticafacile)

-----------------------------------------------------------------------------------

ENGLISH

# 🗑️ Waste Collection for Home Assistant

Custom integration to display your waste collection schedule in Home Assistant, with support for graphic icons and Lovelace visualization.

![HACS Custom](https://img.shields.io/badge/HACS-Custom-blue)
![Platform](https://img.shields.io/badge/Platform-Home%20Assistant-41BDF5)
![Maintainer](https://img.shields.io/badge/Maintainer-DomoticaFacile-blueviolet)
[![Donate](https://img.shields.io/badge/Buy_Me_A_Coffee-%E2%98%95-yellow)](https://www.buymeacoffee.com/domoticafacile)
![GitHub stars](https://img.shields.io/github/stars/DomoticaFacile/raccolta_rifiuti?style=social)

[![Facebook Group](https://img.shields.io/badge/Group-Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white)](https://www.facebook.com/groups/domoticafacile)
[![Facebook Page](https://img.shields.io/badge/Page-Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white)](https://www.facebook.com/domoticafacile)
[![YouTube](https://img.shields.io/badge/YouTube-Channel-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/@DomoticaFacile-it)

[![Instagram](https://img.shields.io/badge/Instagram-Profile-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://www.instagram.com/domoticafacile.it)
[![TikTok](https://img.shields.io/badge/TikTok-Profile-000000?style=for-the-badge&logo=tiktok&logoColor=white)](https://www.tiktok.com/@domoticafacile)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-Channel-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)](https://whatsapp.com/channel/0029Vb5qW5O4o7qPGrFbRm1T)

**Do you like this integration?** ⭐ Click the star to support the project!

![image](https://github.com/user-attachments/assets/2647835f-7981-4974-98c8-f82dcfe85b48)

YouTube Tutorial Video: https://www.youtube.com/watch?v=v-wM2uAQTRg

---

## 📦 Features

✅ Creates the sensor `sensor.raccolta_rifiuti`  
✅ Includes attribute `collection_types` (e.g. `"Plastic", "Paper"`)  
✅ Compatible with templates and custom HTML cards  
✅ Supports images for each waste type  

---

## ⚙️ Installation via HACS

> 💡 If you don’t have HACS yet, follow [this guide](https://hacs.xyz/docs/setup/download)

1. Go to **HACS**
2. Search for “Raccolta Rifiuti” in integrations and click **Install**
3. Restart Home Assistant

---

## 🧾 Configuration

Add this to your `configuration.yaml`:

```yaml
sensor:
  - platform: raccolta_rifiuti
    calendar_entity_id: calendar.raccolta_rifiuti
    # language: auto             # optional: "auto" (default, follows Home Assistant's language), "it" or "en"
    # lookahead_days: 7          # optional (default 7): how many days ahead to look for the next collection if today has none
    # scan_interval: "00:30:00"  # optional: safety-net update interval (default 30 minutes)
    # keywords:                  # optional: your own words used in the calendar
    #   multimateriale: [plastic, metal]
    #   diapers: diapers         # a new code becomes a type of its own
```

The sensor also refreshes right after midnight and whenever the calendar entity changes state. If the calendar is not ready at startup (CalDAV, Google...) the sensor is still created, stays *unavailable* and fills in as soon as the calendar loads. Words are matched as whole words, ignoring case, accents, punctuation and emoji. Codes usable in `keywords`: `paper`, `plastic`, `glass`, `organic`, `residual`, `metal`, `green` (or any new code).

🌍 **Multi-language**: calendar events can be written in Italian or English (e.g. "Carta" or "Paper"), both are recognized. The `language` option only controls the *display* language of the sensor's state and attributes (default: follows Home Assistant's configured language). A `collection_type_codes` attribute is also available, with stable English identifiers (e.g. `"paper"`, `"glass"`), handy for building Lovelace templates that shouldn't depend on the display language.

📅 **Next collection (`lookahead_days`)**: `state` and `collection_types` keep describing only **today's** collection (no change for existing users). In addition, if nothing is scheduled today, the sensor looks ahead up to `lookahead_days` days and populates:
- `days_remaining`: days until the next collection found (`0` if it's today)
- `next_collection_date`: date of the next collection (`YYYY-MM-DD`)
- `next_collection_types` / `next_collection_type_codes`: expected types on that date

Restart Home Assistant.

📆 Creating the Local Calendar (manual setup)

To ensure the integration works correctly, you must manually create a calendar:

Go to Settings > Devices & Services
Click Add Integration
Select “Local Calendar”
Set the name to raccolta_rifiuti (exactly like this)

Add to the calendar (the day before collection) the waste types that will be collected and the time when the card should display the bins.
Allowed values: Paper, Plastic, Glass, Organic, Mixed Waste

Example logic:

If every Monday they collect paper and glass:
Create two events on Sunday
One event for paper, one for glass
Set the time between 19:00–23:59
Repeat weekly for Monday

🧠 Example of HTML Template in Lovelace
```yaml
type: conditional
conditions:
  - condition: state
    entity: calendar.raccolta_rifiuti
    state: "on"
card:
  type: markdown
  content: >-
    {% set raccolta = state_attr('sensor.raccolta_rifiuti', 'collection_types') %}

    Tomorrow the collection includes:

    <div style="display: flex; justify-content: space-evenly; align-items: center;">

    {% if 'Plastic' in raccolta %}
      <img src="/local/images/img_raccolta_rifiuti/plastica.png" style="max-width: 50px; max-height: 50px;" />
    {% endif %}

    {% if 'Paper' in raccolta %}
      <img src="/local/images/img_raccolta_rifiuti/carta.png" style="max-width: 50px; max-height: 50px;" />
    {% endif %}

    {% if 'Glass' in raccolta %}
      <img src="/local/images/img_raccolta_rifiuti/vetro.png" style="max-width: 50px; max-height: 50px;" />
    {% endif %}

    {% if 'Organic' in raccolta %}
      <img src="/local/images/img_raccolta_rifiuti/umido.png" style="max-width: 50px; max-height: 50px;" />
    {% endif %}

    {% if 'Mixed' in raccolta %}
      <img src="/local/images/img_raccolta_rifiuti/indifferenziata.png" style="max-width: 50px; max-height: 50px;" />
    {% endif %}

    </div>
```
🖼️ Images (manual)

After installation, ensure that the following folder exists and contains the images:

```yaml
config\www\images\img_raccolta_rifiuti
```

If the folder is missing, create it manually:

```yaml
Copy the "images" folder from:
config\custom_components\raccolta_rifiuti\
to:
config\www\
```

Restart Home Assistant.

📘 Blueprints (optional but recommended)

To use the included blueprints:

Create the folder:

```swift
config/blueprints/automation/raccolta_rifiuti/
```

Copy into that folder the YAML file from:
https://github.com/DomoticaFacile/raccolta_rifiuti/tree/main/blueprints/automation/raccolta_rifiuti

Restart Home Assistant or reload automations.

👉 After restarting, you’ll find the automation in:
Settings > Automations & Scenes > + Create Automation

🖼️ Screenshots

---
🖼️Screenshots

![image](https://github.com/user-attachments/assets/3b0a8c7b-7e09-4b59-b57e-f7fd8e57a3ae)

![image](https://github.com/user-attachments/assets/bd05df5b-f3ab-4b87-b041-7eba9fef88be)

---

📘 ALEXA VOICE ANNOUNCEMENT CONFIGURATION GUIDE

1️⃣ Create the Helper (Toggle)

Go to: Settings → Devices & Services → Helpers → Create Helper → Toggle

Name the toggle "Avvia Annuncio Raccolta" (this will create input_boolean.avvia_annuncio_raccolta)

Select the "Trash" icon

2️⃣ Expose the Helper to Alexa

Go to:

Settings → Voice Assistants → Expose

Search for "Avvia Annuncio Raccolta"

Make sure the toggle you created is exposed to Alexa

<img width="1155" height="438" alt="image" src="https://github.com/user-attachments/assets/794a6f01-05b9-47d8-8cb9-1be08b78dfaf" />
3️⃣ Create the Routine in Alexa

Open the Amazon Alexa app on your smartphone
→ Routines → +

Trigger → Voice Command
→ "Quali rifiuti devo mettere fuori"
(feel free to add any other trigger you prefer)

Add Action → Smart Home
→ Activate “Avvia Annuncio Raccolta”

Save the routine.

4️⃣ Create a New Automation Using the Blueprint
"Avvia Annuncio raccolta tramite Alexa"
<img width="1025" height="389" alt="image" src="https://github.com/user-attachments/assets/0ab3005a-73f7-4308-8020-fd371b091282" />
🎉 RESULT

How it works:

You: “Alexa, quali rifiuti devo mettere fuori?”

Alexa turns on the helper toggle

The blueprint triggers your main automation

The announcement is played through your preferred Alexa device

The toggle automatically turns itself off

---

👨‍💻 Developer

Created with ❤️ by www.domoticafacile.it

Do you have suggestions or want to contribute?
Open an issue, a pull request, or contact us through our social channels listed on the website.

💖 Acknowledgements

A huge thank you to:

👤 Bilo2110 – for valuable support as a tester 🧪

👤 DaniloGP-91 – for great suggestions in building the Google Home announcement blueprint 🔊

…and thanks to everyone who supports and contributes to this project!

Your feedback, reports, and contributions are always welcome 😊
Together we make home automation easier and more fun!

📄 License

This project is distributed under the MIT license.
You may use, modify, and distribute it freely, as long as the original copyright is preserved.

Read the LICENSE file for full details.
