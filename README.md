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
| 2 | **Local model score** (`binoculars.py`) | Two published zero-shot methods, re-implemented on two small open models (Qwen2.5-0.5B base + instruct): [Binoculars](https://arxiv.org/abs/2401.12070) as the main score and [Fast-DetectGPT](https://arxiv.org/abs/2310.05130) as a second opinion. Machine-generated text is unusually predictable to language models. The score is compared with an **AI-written anchor text** on the same topic and, optionally, with **your own human writing** (one-time calibration) | Local, CPU or GPU; no text leaves your machine |
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

### Pilot evaluation (Turkish, 11 texts)

A small test on Turkish texts with known authors: 3 human texts (a 2019 Wikipedia article, a 2017 Wikipedia talk page, a student's unpunctuated notes), AI texts in default assistant style, and harder cases. Full pipeline (statistics + local models + 3 judges), uncalibrated, CPU.

| Text | Truth | Result | |
|---|---|---|---|
| AI essay (city profile) | AI | 89% | ✓ |
| AI essay (language debate) | AI | 83% | ✓ |
| AI weekly project report, technical | AI | 68% | ✓ local models missed it; judges and statistics caught it |
| AI text with a chatbot leftover ("I hope this helps") | AI | ≥ 95% (definitive signal) | ✓ |
| Wikipedia article (2019) | human | 16% | ✓ |
| Wikipedia talk page (2017) | human | 7% | ✓ |
| Student's raw notes, no punctuation | human | ~10% | ✓ |
| Project draft: AI draft + student edits | mixed | 41%, low confidence | ~ undecided |
| Student's notes, lightly edited by AI, facts kept | mixed | 33%; judges flagged "human content, AI polish" | ~ |
| **AI text paraphrased into a casual style** | **AI** | **24%** | **✗ missed** |

Model signals on the same texts (lower Binoculars r / higher Fast-DetectGPT = more AI-like):

| | Binoculars r vs. AI anchor | Fast-DetectGPT |
|---|---|---|
| AI, default style (3 texts) | 0.93 – 0.98 | 3.35 – 4.54 |
| AI, technical report | 1.07 | 1.69 |
| AI, paraphrased / imitating a human | 1.18 – 1.20 | −0.69 – −0.55 |
| Human (3 texts) | 1.07 – 1.13 | 0.34 – 2.86 |

What this shows:
- Default-style AI text and unedited human text are separated well.
- **Paraphrased AI text gets through.** Simple rewording into short, casual sentences fooled the statistics, both model scores and most judges. This matches the literature (Krishna et al., 2023).
- Encyclopedic human writing looks machine-like to the model scores (Fast-DetectGPT flagged the Wikipedia article); the judges and statistics corrected it.
- 11 texts is a sanity check, not a benchmark. Thresholds were set on this pilot and may not transfer.

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
- **Paraphrased or "humanized" AI text is largely missed.** In the pilot, a simple casual rewrite dropped an AI text from 68% to 24%. This is a known weakness of all current detectors (Krishna et al., 2023). A low score never proves a human wrote the text.
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
examples/                # two short Turkish test texts, BOTH machine-written:
                         #   ai_style_tr.txt    default assistant style
                         #   human_style_tr.txt AI imitating casual human notes (a hard case)
```

### References

- Hans et al., 2024. *Spotting LLMs With Binoculars: Zero-Shot Detection of Machine-Generated Text.* [arXiv:2401.12070](https://arxiv.org/abs/2401.12070)
- Bao et al., 2024. *Fast-DetectGPT: Efficient Zero-Shot Detection of Machine-Generated Text via Conditional Probability Curvature.* [arXiv:2310.05130](https://arxiv.org/abs/2310.05130)
- Krishna et al., 2023. *Paraphrasing evades detectors of AI-generated text, but retrieval is an effective defense.* [arXiv:2303.13408](https://arxiv.org/abs/2303.13408)
- Liang et al., 2023. *GPT detectors are biased against non-native English writers.* [arXiv:2304.02819](https://arxiv.org/abs/2304.02819)
- Survey: *Towards Possibilities & Impossibilities of AI-generated Text Detection.* [arXiv:2310.15264](https://arxiv.org/abs/2310.15264)

### License

MIT (see `LICENSE`). The Qwen2.5 models are downloaded from Hugging Face under their own license (Apache 2.0).

Acknowledgements: the model scores re-implement the methods of [Binoculars](https://github.com/ahans30/Binoculars) (BSD-3-Clause) and [Fast-DetectGPT](https://github.com/baoguangsheng/fast-detect-gpt) (MIT) from their papers; no code was copied. Turkish test texts from Wikipedia (CC BY-SA) were used only for evaluation and are not included in this repository.

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
| 2 | **Yerel model skoru** (`binoculars.py`) | Yayımlanmış iki sıfır-örnek (zero-shot) yöntem, iki küçük açık model (Qwen2.5-0.5B temel + instruct) üzerinde yeniden uygulandı: ana skor [Binoculars](https://arxiv.org/abs/2401.12070), ikinci görüş [Fast-DetectGPT](https://arxiv.org/abs/2310.05130). Makine metni dil modellerine alışılmadık derecede "tahmin edilebilir" gelir. Skor, aynı konuda yazılmış bir **yapay zekâ referans metniyle** ve isteğe bağlı olarak **senin kendi yazılarınla** (tek seferlik kalibrasyon) karşılaştırılır | Yerel, CPU veya GPU; metin bilgisayardan çıkmaz |
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

### Pilot değerlendirme (Türkçe, 11 metin)

Yazarı bilinen Türkçe metinlerle küçük bir test: 3 insan metni (2019 tarihli bir Vikipedi maddesi, 2017 tarihli bir Vikipedi tartışma sayfası, bir öğrencinin noktalamasız notları), varsayılan asistan üslubunda yapay zekâ metinleri ve daha zor durumlar. Tam akış (istatistik + yerel modeller + 3 hakem), kalibrasyonsuz, CPU.

| Metin | Gerçek | Sonuç | |
|---|---|---|---|
| YZ denemesi (şehir tanıtımı) | YZ | %89 | ✓ |
| YZ denemesi (dil tartışması) | YZ | %83 | ✓ |
| YZ haftalık proje raporu, teknik | YZ | %68 | ✓ yerel modeller kaçırdı; jüri ve istatistik yakaladı |
| Sohbet botu artığı içeren YZ metni ("Umarım yardımcı olur") | YZ | ≥ %95 (kesin işaret) | ✓ |
| Vikipedi maddesi (2019) | insan | %16 | ✓ |
| Vikipedi tartışma sayfası (2017) | insan | %7 | ✓ |
| Öğrencinin noktalamasız ham notları | insan | ~%10 | ✓ |
| Proje taslağı: YZ taslağı + öğrenci düzenlemeleri | karışık | %41, düşük güven | ~ kararsız |
| Öğrenci notlarının YZ ile hafifçe düzenlenmiş hâli (bilgiler aynı) | karışık | %33; hakemler "içerik insanın, cila YZ'nin" dedi | ~ |
| **Gündelik üsluba çevrilmiş YZ metni** | **YZ** | **%24** | **✗ kaçırıldı** |

Bu ne gösteriyor:
- Varsayılan üslupta YZ metni ile düzenlenmemiş insan metni iyi ayrışıyor.
- **Yeniden ifade edilmiş YZ metni yakalanmıyor.** Kısa ve gündelik cümlelerle yapılan basit bir yeniden yazım; istatistikleri, iki model skorunu ve hakemlerin çoğunu kandırdı. Bu, literatürle tutarlı (Krishna vd., 2023).
- Ansiklopedik insan yazısı model skorlarına makine gibi görünebiliyor (Fast-DetectGPT Vikipedi maddesini işaretledi); jüri ve istatistik bunu düzeltti.
- 11 metin bir sağlama testidir, kıyaslama (benchmark) değil. Eşikler bu pilota göre ayarlandı; başka metinlere aynen geçmeyebilir.

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
- **Yeniden ifade edilmiş ya da "insanlaştırılmış" YZ metni büyük ölçüde kaçırılır.** Pilotta basit bir gündelik yeniden yazım, bir YZ metnini %68'den %24'e düşürdü. Bu, mevcut tüm dedektörlerin bilinen bir zayıflığıdır (Krishna vd., 2023). Düşük bir skor, metni bir insanın yazdığını asla kanıtlamaz.
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

Teşekkür: model skorları [Binoculars](https://github.com/ahans30/Binoculars) (BSD-3-Clause) ve [Fast-DetectGPT](https://github.com/baoguangsheng/fast-detect-gpt) (MIT) yöntemlerini makalelerinden yeniden uygular; kod kopyalanmamıştır. Vikipedi'den alınan Türkçe test metinleri (CC BY-SA) sadece değerlendirme için kullanıldı ve bu repoya eklenmedi.
