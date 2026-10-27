from pathlib import Path

from ijro.benchmark import run
from ijro.extract import Extraction


class FakeExtractor:
    def __init__(self, answers):
        self.answers = answers
        self.models = []

    def run(self, source: Path, out_dir: Path, model=None):
        self.models.append(model)
        answer = self.answers[source.name]
        if isinstance(answer, Exception):
            raise answer
        return Extraction(answer, {}, 1, 1)


def test_benchmark_counts_correct_empty_and_wrong(tmp_path):
    (tmp_path / "kutilgan.csv").write_text(
        "fayl;royxat_raqami;royxat_sanasi;chiqish_raqami;ijro_muddati_sana;ijrochilar\n"
        "a.pdf;488-PA;2026-10-01;26-2850;2026-10-12;U.Xoshimova, TTPU\n"
        "b.pdf;12-PA;2026-10-02;;;TTPU\n"
        "c.pdf;13-PA;2026-10-03;;;TTPU\n", encoding="utf-8-sig")
    fx = FakeExtractor({
        "a.pdf": {"reg_no": "488-РА", "reg_date": "2026-10-01", "out_no": "26-2851", "due_date": "",
                  "resolution": "TTPU,\nXoshimova U."},
        "b.pdf": {"reg_no": "", "reg_date": "2026-10-02", "out_no": "", "due_date": "", "resolution": "TTPU"},
        "c.pdf": RuntimeError("Ollama ishlamayapti"),
    })
    report = run(fx, tmp_path, ["m1"])
    assert fx.models == ["m1", "m1", "m1"]
    rows = {line.split()[0]: line.split()[1:] for line in report.splitlines() if line.startswith(("royxat", "chiqish", "ijro"))}
    assert rows["royxat_raqami"] == ["1", "1", "0"]
    assert rows["royxat_sanasi"] == ["2", "0", "0"]
    assert rows["chiqish_raqami"] == ["1", "0", "1"]
    assert rows["ijro_muddati_sana"] == ["1", "1", "0"]
    assert rows["ijrochilar"] == ["2", "0", "0"]
    assert "o'qilmadi: 1" in report
