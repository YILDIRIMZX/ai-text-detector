# AI Text Detector — Agent Skill

**[English](#english) · [Türkçe](#türkçe)**

An agent skill that estimates whether a text was written by AI, gives the result as a **percentage with a confidence level**, and explains **why**: quoted evidence for AI authorship, quoted evidence for human authorship, and a paragraph-by-paragraph breakdown. Works with Turkish and English.

> ⚠️ This tool gives a **probability estimate, not proof**. Read [Limitations](#limitations) before using it on someone else's work.

---

## English

### What it does

- Gives an **AI probability (0–100%)** with an uncertainty range (e.g. 62%, range 48–76%) and a confidence level (high / medium / low).
- Explains the result with **exact quotes**: lines that look machine-written and lines that look human, each with a reason.
- Scores **each paragraph** separately, so mixed texts (part human, part AI) show where the change happens.
- Lists the **reasons the result could be wrong** for this specific text.
- Three modes:
  - **Own text**: ends with concrete advice to make your writing sound more like you.
  - **Someone else's text**: adds a fair-use section (don't accuse anyone based on this alone).
  - **Technical document / code comments**: down-weights signals that are normal for structured writing.

### How it works

The skill combines four independent signals, because none of them is reliable on its own.

| # | Signal | What it measures | Runs |
|---|---|---|---|
| 1 | **Stylometric statistics** (`ai_stats.py`) | Sentence-length variation ("burstiness"), vocabulary diversity (MATTR), rates of AI-typical phrases in Turkish and English (stock openers, overused connectors, inflated adjectives, hedges), list/heading/triad structure, repetition | Local, Python standard library only |
| 2 | **Local model score** (`binoculars.py`) | A zero-shot [Binoculars](https://arxiv.org/abs/2401.12070)-style score from two small open models (Qwen2.5-0.5B base + instruct). Machine-generated text is unusually predictable to language models. The score is compared with an **AI-written anchor text** on the same topic and, optionally, with **your own human writing** (one-time calibration) | Local, CPU or GPU; no text leaves your machine |
| 3 | **Definitive signals** | Chatbot leftovers ("As an AI language model…", "I hope this helps"), unfilled placeholders, and, for academic texts, **citations that don't exist** (checked by web search) | Agent |
| 4 | **Blind judge panel** | Three independent judges (stylometrist, content analyst, devil's advocate who argues for human authorship) read the text separately. Their judgments are then **anonymously cross-reviewed and ranked**, so weak judgments count less | Agent sub-agents |

**Combining:** final score = 50% judges (rank-weighted) + 20–35% model score + 15% statistics, renormalized if a part is missing. A confirmed definitive signal sets the score to at least 95%. The uncertainty range widens when the signals disagree.

```
text ──► statistics ─────────┐
     ├─► local models ───────┤
     ├─► definitive checks ──┼──► weighted score + range + confidence ──► report
     └─► 3 blind judges ──► anonymous cross-review ──┘
```

### Installation

1. Copy `skills/ai-detector/` into your agent's skills directory (any agent that supports `SKILL.md` skills).
2. *(Optional, for signal 2)* Install the local model environment (about 200 MB of libraries + 2 × ~1 GB models, downloaded once):
   - Windows: `powershell -ExecutionPolicy Bypass -File skills/ai-detector/scripts/setup.ps1` (add `-Cuda` for an NVIDIA GPU)
   - Linux / macOS: `sh skills/ai-detector/scripts/setup.sh` (`CUDA=1` for an NVIDIA GPU on Linux)
   Without it, the skill still runs with signals 1, 3 and 4 and says so in the report.
3. *(Optional)* Calibrate with 2–3 texts you certainly wrote yourself (ideally from before 2022). This gives the model score a human reference point and raises its weight.

### Usage

Ask your agent in plain language, e.g.:
- "Is this text AI-generated? `essay.docx`"
- "Bu metin yapay zekâ ile mi yazılmış?" + pasted text
- "Check my report before I submit it, does it read like AI?"

### Real results on the example texts

Signals 1–3 measured on the two Turkish samples in `examples/` (CPU, uncalibrated, AI anchor written on the same topic). Both texts are short (~100 words), so a full report would mark confidence as low.

| | `ai_style_tr.txt` | `human_style_tr.txt` |
|---|---|---|
| Sentence-length variation (burstiness CV) | 0.23 (very uniform) | 0.46 (mixed) |
| AI-typical phrases per 1000 words | 174.7 | 0 |
| Binoculars vs. AI anchor (r, lower = more machine-like) | 0.93 → model score ≈ 90 | 1.18 → model score ≈ 36 |
| Definitive signal | "Umarım bu bilgiler yardımcı olur" (chatbot leftover) | none |
| Outcome | ≥ 95% AI (definitive signal) | low AI probability; the judge panel decides the final number |

Report format (shortened):

```
## Result: X% AI probability (range A–B% · confidence: low/medium/high)
| Signal | Score (0 human – 100 AI) | Note |
Why it may be AI:    "<exact quote>" → reason
Why it may be human: "<exact quote>" → reason
Paragraph by paragraph: ¶1 … ¶2 … ¶3 …
Why this result may be wrong: …
```

### What it can do

- Explain its reasoning with quotes instead of giving a bare number.
- Show mixed authorship at paragraph level.
- Work in Turkish and English, with language-specific phrase lists.
- Run the statistical and model parts fully offline.
- Catch definitive evidence (chatbot leftovers, fabricated citations) with high confidence.
- Adapt to you: calibration with your own writing makes the model score more meaningful.

### Limitations

- **It cannot prove authorship.** No detector can. Published studies show AI detectors misclassify human writing, especially by **non-native speakers** (one widely cited study found an average false-positive rate of 61% on non-native English essays), and that current tools are not reliable for high-stakes decisions such as grading or misconduct cases.
- **Short texts** (< 150 words) give low-confidence results; under ~50 words it refuses to give a percentage.
- **Edited or paraphrased AI text** (rewritten by a person or a "humanizer") is much harder to detect, and false negatives are likely.
- **Formulaic genres** (CVs, legal text, forms, technical docs, school essays written to a template) look machine-like even when human-written.
- **Grammar tools and translation** shift scores toward "AI".
- The **local model score is uncalibrated** for this small model pair until you calibrate it; on its own it is a weak signal. Small models are less accurate than the large models used in the original Binoculars paper, and Turkish performance is less studied than English.
- The judge panel uses language models, which share some of the same biases.
- **Not benchmarked**: there is no published accuracy figure for this skill. Treat the percentage as a structured opinion.

### Responsible use

- Don't accuse, grade down or punish anyone based on this report alone. Talk to the author and ask about drafts, notes or version history.
- When used on your own writing, the aim is clearer, more personal writing, not hiding AI use where it is not allowed.

### Privacy

The statistics and model scores run locally. The text is never sent to third-party detector websites. The judge panel runs inside your agent, so the text is processed by whatever model your agent uses.

### Repository layout

```
skills/ai-detector/
  SKILL.md               # instructions the agent follows
  scripts/ai_stats.py    # stylometric statistics (stdlib only)
  scripts/binoculars.py  # local two-model score
  scripts/setup.ps1      # environment setup (Windows)
  scripts/setup.sh       # environment setup (Linux/macOS)
examples/                # sample AI-style and human-style Turkish texts
```

### References

- Hans et al., 2024. *Spotting LLMs With Binoculars: Zero-Shot Detection of Machine-Generated Text.* [arXiv:2401.12070](https://arxiv.org/abs/2401.12070)
- Liang et al., 2023. *GPT detectors are biased against non-native English writers.* [arXiv:2304.02819](https://arxiv.org/abs/2304.02819)
- Survey: *Towards Possibilities & Impossibilities of AI-generated Text Detection.* [arXiv:2310.15264](https://arxiv.org/abs/2310.15264)

### License

MIT (see `LICENSE`). The Qwen2.5 models are downloaded from Hugging Face under their own license (Apache 2.0).

---

## Türkçe

### Ne işe yarar?

Bir metnin yapay zekâ tarafından yazılıp yazılmadığını **yüzde ve güven seviyesiyle** tahmin eder, ve **nedenini** açıklar: yapay zekâya işaret eden ve insana işaret eden satırları alıntılayarak, paragraf paragraf. Türkçe ve İngilizce metinlerde çalışır.

> ⚠️ Bu araç bir **tahmin** verir, **kanıt** değil. Başkasının metninde kullanmadan önce [Sınırlar](#sınırlar) bölümünü okuyun.

- **Yapay zekâ olasılığı (%0–100)**, bir belirsizlik aralığı (ör. %62, aralık %48–76) ve güven seviyesi (yüksek / orta / düşük).
- Gerekçeler **birebir alıntılarla**: hangi satır neden makine gibi, hangisi neden insan gibi duruyor.
- **Her paragraf ayrı puanlanır**; karışık metinlerde (bir kısmı insan, bir kısmı yapay zekâ) geçişin nerede olduğu görünür.
- Bu metin için **sonucun neden yanlış olabileceği** ayrıca listelenir.
- Üç mod:
  - **Kendi metnin:** sonunda yazını daha "senin gibi" yapacak somut öneriler.
  - **Başkasının metni:** adil kullanım bölümü eklenir (yalnızca buna dayanarak kimse suçlanmamalı).
  - **Teknik belge / kod yorumları:** yapılandırılmış yazıda normal olan sinyallerin ağırlığı düşürülür.

### Nasıl çalışır?

Tek başına hiçbiri güvenilir olmadığı için dört bağımsız sinyali birleştirir:

| # | Sinyal | Ne ölçer | Nerede çalışır |
|---|---|---|---|
| 1 | **Biçemsel istatistikler** (`ai_stats.py`) | Cümle uzunluğu çeşitliliği, kelime çeşitliliği (MATTR), Türkçe ve İngilizce yapay zekâ kalıplarının sıklığı ("günümüzde", "önemli bir rol oynar", "bunun yanı sıra", "kapsamlı/etkili/yenilikçi"…), liste/başlık/üçlü yapı, tekrarlar | Yerel, sadece Python standart kütüphanesi |
| 2 | **Yerel model skoru** (`binoculars.py`) | İki küçük açık modelle (Qwen2.5-0.5B temel + instruct) [Binoculars](https://arxiv.org/abs/2401.12070) yöntemine benzer bir skor. Makine metni dil modellerine alışılmadık derecede "tahmin edilebilir" gelir. Skor, aynı konuda yazılmış bir **yapay zekâ referans metniyle** ve isteğe bağlı olarak **senin kendi yazılarınla** (tek seferlik kalibrasyon) karşılaştırılır | Yerel, CPU veya GPU; metin bilgisayardan çıkmaz |
| 3 | **Kesin işaretler** | Sohbet botu artıkları ("Bir yapay zekâ modeli olarak…", "Umarım yardımcı olur"), doldurulmamış yer tutucular ve akademik metinlerde **var olmayan kaynaklar** (web aramasıyla kontrol edilir) | Ajan |
| 4 | **Kör jüri** | Üç bağımsız hakem (biçem uzmanı, içerik analisti, metnin insan yazısı olduğunu savunan "şeytanın avukatı") metni ayrı ayrı okur. Sonra kararları **isimsiz olarak çapraz değerlendirilir ve sıralanır**; zayıf kararların ağırlığı düşer | Ajan alt-ajanları |

**Birleştirme:** sonuç = %50 jüri (sıralamaya göre ağırlıklı) + %20–35 model skoru + %15 istatistik; eksik parça varsa yeniden normalize edilir. Doğrulanmış bir kesin işaret sonucu en az %95'e çeker. Sinyaller birbiriyle çeliştikçe belirsizlik aralığı genişler.

### Kurulum

1. `skills/ai-detector/` klasörünü ajanının skill klasörüne kopyala (`SKILL.md` skill'lerini destekleyen her ajan olur).
2. *(İsteğe bağlı, 2. sinyal için)* Yerel model ortamını kur (yaklaşık 200 MB kütüphane + 2 × ~1 GB model, bir kez indirilir):
   - Windows: `powershell -ExecutionPolicy Bypass -File skills/ai-detector/scripts/setup.ps1` (NVIDIA ekran kartı için `-Cuda` ekle)
   - Linux / macOS: `sh skills/ai-detector/scripts/setup.sh` (Linux'ta NVIDIA için `CUDA=1`)
   Kurulmazsa skill 1, 3 ve 4. sinyallerle çalışmaya devam eder ve bunu raporda belirtir.
3. *(İsteğe bağlı)* Kesinlikle kendi yazdığın 2–3 metinle (tercihen 2022 öncesi) kalibrasyon yap. Model skoruna insan referansı kazandırır ve ağırlığını artırır.

### Kullanım

Ajana düz bir dille sor:
- "Bu metin yapay zekâ ile mi yazılmış? `odev.docx`"
- "Raporumu teslim etmeden önce kontrol et, YZ gibi duruyor mu?"
- "Is this text AI-generated?" + yapıştırılmış metin

### Örnek metinlerde gerçek sonuçlar

`examples/` klasöründeki iki Türkçe örnekte 1–3. sinyallerin ölçümü (CPU, kalibrasyonsuz, aynı konuda yazılmış YZ referansıyla). İki metin de kısa (~100 kelime), bu yüzden tam raporda güven "düşük" olarak işaretlenir.

| | `ai_style_tr.txt` | `human_style_tr.txt` |
|---|---|---|
| Cümle uzunluğu çeşitliliği (burstiness CV) | 0,23 (çok tekdüze) | 0,46 (karışık) |
| 1000 kelimede YZ kalıbı | 174,7 | 0 |
| YZ referansına göre Binoculars (r, düşük = daha makine gibi) | 0,93 → model skoru ≈ 90 | 1,18 → model skoru ≈ 36 |
| Kesin işaret | "Umarım bu bilgiler yardımcı olur" (sohbet botu artığı) | yok |
| Sonuç | ≥ %95 YZ (kesin işaret) | düşük YZ olasılığı; son sayıyı jüri belirler |

### Neler yapabilir?

- Çıplak bir sayı yerine gerekçesini alıntılarla açıklar.
- Karışık yazımı paragraf düzeyinde gösterir.
- Türkçe ve İngilizce için ayrı kalıp listeleriyle çalışır.
- İstatistik ve model kısımlarını tamamen çevrimdışı çalıştırır.
- Kesin kanıtları (sohbet botu artıkları, uydurma kaynaklar) yüksek güvenle yakalar.
- Sana uyum sağlar: kendi yazılarınla kalibrasyon, model skorunu daha anlamlı hale getirir.

### Sınırlar

- **Yazarı kanıtlayamaz.** Hiçbir dedektör kanıtlayamaz. Yayımlanmış çalışmalar yapay zekâ dedektörlerinin insan yazısını, özellikle **anadili farklı olan yazarların** metinlerini hatalı işaretlediğini gösteriyor (sık atıf alan bir çalışmada anadili İngilizce olmayan öğrencilerin makalelerinde ortalama yanlış alarm oranı %61). Mevcut araçlar not verme ya da disiplin gibi yüksek riskli kararlar için güvenilir değil.
- **Kısa metinlerde** (< 150 kelime) güven düşüktür; ~50 kelimenin altında yüzde verilmez.
- **Düzenlenmiş ya da başka sözcüklerle yeniden yazılmış** yapay zekâ metinlerini yakalamak çok daha zordur; gözden kaçırma olasılığı yüksektir.
- **Kalıplı türler** (CV, hukuki metin, form, teknik belge, şablona göre yazılmış okul ödevi) insan yazısı olsa bile makine gibi görünebilir.
- **Dilbilgisi araçları ve çeviri** skoru "yapay zekâ" yönüne kaydırır.
- **Yerel model skoru**, sen kalibre edene kadar bu küçük model çifti için kalibre değildir; tek başına zayıf bir sinyaldir. Küçük modeller, orijinal Binoculars çalışmasındaki büyük modellerden daha az isabetlidir; Türkçedeki başarısı İngilizceye göre daha az incelenmiştir.
- Jüri de dil modelleriyle çalışır ve benzer önyargıları paylaşabilir.
- **Doğruluk testi yapılmamıştır**: bu skill için yayımlanmış bir başarı oranı yoktur. Yüzdeyi yapılandırılmış bir görüş olarak değerlendirin.

### Sorumlu kullanım

- Yalnızca bu rapora dayanarak kimseyi suçlamayın, notunu düşürmeyin ya da cezalandırmayın. Yazarla konuşun; taslaklarını, notlarını ya da sürüm geçmişini sorun.
- Kendi yazınızda kullanırken amaç daha net ve kişisel yazmaktır; yapay zekânın yasak olduğu işlerde kullanımı gizlemek değil.

### Gizlilik

İstatistik ve model skorları yerelde çalışır. Metin hiçbir üçüncü taraf dedektör sitesine gönderilmez. Jüri ajanın içinde çalıştığı için metin, ajanın kullandığı model tarafından işlenir.

### Lisans

MIT (`LICENSE` dosyasına bakın). Qwen2.5 modelleri Hugging Face'ten kendi lisanslarıyla (Apache 2.0) indirilir.
