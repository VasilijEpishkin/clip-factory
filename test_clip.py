from clip import validate, crop_x, caption_events, x_expr, ass_time

WORDS = [{"w": f"w{i}", "s": i * 0.5, "e": i * 0.5 + 0.4} for i in range(400)]  # 0..200 s


def test_validate_snaps_to_word_boundaries():
    [c] = validate([{"start": 10.6, "end": 40.3}], WORDS)
    assert (c["start"], c["end"]) == (10.5, 40.4)


def test_validate_trims_too_long_and_extends_slightly_short():
    [long_] = validate([{"start": 0, "end": 90}], WORDS)
    assert long_["end"] - long_["start"] <= 45
    [short] = validate([{"start": 100, "end": 118}], WORDS)  # 18 s -> extended to >= 20
    assert 20 <= short["end"] - short["start"] <= 45


def test_validate_drops_bad_overlap_and_garbage():
    cands = [{"start": 0, "end": 30}, {"start": 10, "end": 35}, {"start": "x"}, {"start": 50, "end": 52},
             {"start": 150, "end": 500}, {"start": 60, "end": 90}]
    got = validate(cands, WORDS)
    assert [round(c["start"]) for c in got] == [0, 60]  # overlap, garbage, too short, past-the-end dropped
    assert all(c["end"] <= 199.9 for c in got)


def test_crop_x_centres_and_clamps():
    assert crop_x(0.5, 1920, 1080) == (657, 606)
    assert crop_x(0.0, 1920, 1080)[0] == 0
    assert crop_x(1.0, 1920, 1080)[0] == 1920 - 606
    assert crop_x(0.5, 500, 1080) == (0, 500)  # source narrower than 9:16


def test_x_expr():
    assert x_expr([(0, 10)]) == "10"
    assert x_expr([(0, 10), (2.5, 20), (7, 30)]) == "if(lt(t,2.500),10,if(lt(t,7.000),20,30))"


def test_caption_events_timing():
    ws = [{"w": "Hello", "s": 10.0, "e": 10.4}, {"w": "big", "s": 10.5, "e": 10.8}, {"w": "world.", "s": 10.9, "e": 11.3},
          {"w": "Next", "s": 11.4, "e": 11.7}, {"w": "late", "s": 13.0, "e": 13.4}, {"w": "after", "s": 14.5, "e": 14.8}]
    ev = caption_events(ws, 10.0, 15.0)
    assert len(ev) == 6
    assert ev[0][:2] == (0.0, 0.5)          # held until next word starts
    assert ev[2][:2] == (0.9, 1.4)          # chunk end bridges small gap to next chunk
    assert ev[3][:2] == (1.4, 1.7)          # gap to "late" 1.3 s >= 1.2 s: ends at word end
    assert ev[4][:2] == (3.0, 4.5)          # gap to "after" 1.1 s < 1.2 s: held until it starts
    assert "{\\c&H00E5FF&}HELLO" in ev[0][2] and "WORLD." in ev[0][2] and "NEXT" not in ev[0][2]
    assert all(0 <= a < b <= 5.0 for a, b, _ in ev)


def test_ass_time():
    assert ass_time(0) == "0:00:00.00" and ass_time(3723.456) == "1:02:03.46"


def test_banner_never_repeats_spoken_hook():
    from clip import banner_text
    hook = "Did you always want to be an astronaut? I did."
    assert banner_text({"hook": hook, "caption": "NASA astronaut on her childhood", "title": "T"}) == "NASA astronaut on her childhood"
    assert banner_text({"hook": hook, "caption": "Always wanted to be an astronaut?", "title": "Knew at 3"}) == "Knew at 3"
    assert banner_text({"hook": hook, "title": "Knew at 3"}) == "Knew at 3"


def _ws(text, t0=0.0, step=0.3):
    return [{"w": w, "s": round(t0 + i * step, 2), "e": round(t0 + i * step + 0.25, 2)} for i, w in enumerate(text.split())]


def test_filler_start():
    from clip import filler_start
    for t in ["And, you know, one", "So here", "You know what", "um okay", "Like, really", "But then"]:
        assert filler_start(_ws(t)), t
    for t in ["Did you always", "Knowledge is", "Sometimes I", "Younger kids"]:
        assert not filler_start(_ws(t)), t


def test_skip_filler_prefers_sentence_start_then_strips_run():
    from clip import skip_filler
    ws = _ws("so yeah. One of the biggest barriers")       # sentence start at 0.6 s
    assert ws[skip_filler(ws, 0)]["w"] == "One"
    ws = _ws("And, you know, one of the biggest barriers")  # no sentence start: drop the filler run
    assert ws[skip_filler(ws, 0)]["w"] == "one"
    ws = _ws("Did you always want")
    assert skip_filler(ws, 0) == 0
    ws = _ws("and " * 8 + "finally", step=0.3)               # clean word 2.4 s away: give up
    assert skip_filler(ws, 0) is None


def test_validate_moves_start_off_filler():
    ws = WORDS[:20] + _ws("And, you know, one of the biggest barriers " + "w " * 80, t0=10.0)
    [c] = validate([{"start": 10.0, "end": 35.0}], ws)
    assert c["start"] == 10.9  # "one"


def test_heatmap_peaks_and_preference():
    from clip import heatmap_peaks, peaks_block
    hm = [{"start_time": i * 10.0, "end_time": i * 10.0 + 10, "value": v}
          for i, v in enumerate([1.0, .1, .2, .9, .8, .1, .1, .7, .1, .1])]
    assert heatmap_peaks(hm, k=3) == [(30.0, 50.0, .9), (70.0, 80.0, .7)]  # bucket 0 ignored, 30-40 + 40-50 merged
    assert "[30.0-50.0] replay=0.90" in peaks_block(heatmap_peaks(hm, k=3)) and peaks_block([]) == ""
    cands = [{"start": 100, "end": 125}, {"start": 0, "end": 25}, {"start": 30, "end": 55}]
    got = validate(cands, WORDS, n=2, peaks=[(40.0, 50.0, .9)])
    assert [round(c["start"]) for c in got] == [30, 100]  # peak overlap first, then LLM order


def test_hooks_block_and_hook_type():
    from clip import hooks_block
    hooks = [{"hook_type": "question", "template": "Did you {X}?", "example": "Did you know?", "evidence": "lift 2x"},
             {"bad": 1}] + [{"hook_type": "contrarian", "template": f"t{i}"} for i in range(30)]
    b = hooks_block(hooks)
    assert b.count("\n") == 16 and b.splitlines()[1] == '- question: "Did you {X}?" e.g. "Did you know?" [lift 2x]'  # header+14, blank
    assert hooks_block([]) == ""
    [c] = validate([{"start": 10, "end": 40, "hook_type": "made_up"}], WORDS)
    assert c["hook_type"] == "other"
