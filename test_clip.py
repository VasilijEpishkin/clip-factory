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
          {"w": "Next", "s": 11.4, "e": 11.7}, {"w": "late", "s": 13.0, "e": 13.4}]
    ev = caption_events(ws, 10.0, 14.0)
    assert len(ev) == 5
    assert ev[0][:2] == (0.0, 0.5)          # held until next word starts
    assert ev[2][:2] == (0.9, 1.4)          # chunk end bridges small gap to next chunk
    assert ev[3][:2] == (1.4, 1.7)          # gap to "late" > 0.3 s: ends at word end
    assert "{\\c&H00E5FF&}HELLO" in ev[0][2] and "WORLD." in ev[0][2] and "NEXT" not in ev[0][2]
    assert all(0 <= a < b <= 4.0 for a, b, _ in ev)


def test_ass_time():
    assert ass_time(0) == "0:00:00.00" and ass_time(3723.456) == "1:02:03.46"
