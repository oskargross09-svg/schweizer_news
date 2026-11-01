"""German voiceover with Piper (Thorsten, high).

Usage as CLI:  python3 pipeline/tts.py check Wort1 Wort2 ...   -> prints phonemes (to spot bad pronunciation)
               python3 pipeline/tts.py say "Ein Satz." out.wav
"""
import os, re, sys
import numpy as np

M = os.environ.get("SN_MODELS", os.path.expanduser("~/.cache/swiss-news/models"))
VOICE = f"{M}/vits-piper-de_DE-thorsten-high/de_DE-thorsten-high.onnx"
LENGTH_SCALE = 0.86   # < 1 = faster (Swiss News is a bit faster than Daily News)
GAP = 0.16            # pause between sentences, s

# phoneme fixes that always apply (English words / brand)
PH_FIX = {
    "svˈɪs njˈuːz": "swˈɪs njˈuːs",
    "hˌaloːvˈeːən": "hˈɛloviːn",
    "ŋkzɛkstr": "ŋksɛkstr",
}
_voice = None


def voice():
    global _voice
    if _voice is None:
        from piper import PiperVoice
        _voice = PiperVoice.load(VOICE)
    return _voice


def respell(text, say):
    for a, b in (say or {}).items():
        text = re.sub(rf"(?<!\w){re.escape(a)}(?!\w)", b, text)
    return text


def synth(text, say=None):
    """-> (float32 audio, sample_rate, [sentence start offsets in s])"""
    from piper import SynthesisConfig
    v = voice()
    sr = v.config.sample_rate
    syn = SynthesisConfig(length_scale=LENGTH_SCALE, noise_scale=0.6, noise_w_scale=0.7)
    out, offs, pos = [], [], 0
    for sent in v.phonemize(respell(text, say)):
        ph = "".join(sent)
        for a, b in PH_FIX.items():
            ph = ph.replace(a, b)
        a = np.asarray(v.phoneme_ids_to_audio(v.phonemes_to_ids(list(ph)), syn), dtype=np.float32)
        i = np.where(np.abs(a) > 0.01)[0]
        if len(i) == 0:
            continue
        a = a[max(i[0] - 300, 0): i[-1] + 1500]
        offs.append(round(pos / sr, 3))
        gap = np.zeros(int(GAP * sr), np.float32)
        out += [a, gap]
        pos += len(a) + len(gap)
    return np.concatenate(out[:-1]), sr, offs


if __name__ == "__main__":
    if sys.argv[1] == "check":
        v = voice()
        for w in sys.argv[2:]:
            print(w, "->", "".join(sum(v.phonemize(w), [])))
    elif sys.argv[1] == "say":
        import soundfile as sf
        a, sr, _ = synth(sys.argv[2])
        sf.write(sys.argv[3], a, sr)
