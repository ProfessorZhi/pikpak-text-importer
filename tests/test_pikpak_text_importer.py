import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from pikpak_importer.importer import extract_share_entries, extract_share_links, parse_share_link


class ExtractShareLinksTests(unittest.TestCase):
    def test_extract_links_keeps_order_and_deduplicates(self) -> None:
        text = """
        这里有两个链接：
        https://mypikpak.com/s/AAA111
        重复一次 https://mypikpak.com/s/AAA111
        再来一个 https://mypikpak.com/s/BBB222/CCC333
        """

        links = extract_share_links(text)

        self.assertEqual(
            [link.url for link in links],
            [
                "https://mypikpak.com/s/AAA111",
                "https://mypikpak.com/s/BBB222/CCC333",
            ],
        )
        self.assertEqual(links[1].nested_id, "CCC333")

    def test_parse_share_link(self) -> None:
        link = parse_share_link("https://mypikpak.com/s/VOiDfXZdTPWg9IXe8OQIohbQo2")
        self.assertEqual(link.share_id, "VOiDfXZdTPWg9IXe8OQIohbQo2")
        self.assertIsNone(link.nested_id)

    def test_extract_entries_uses_following_line_as_folder_label(self) -> None:
        text = """
        https://mypikpak.com/s/AAA111
        设计文档集合

        https://mypikpak.com/s/BBB222
        项目资料归档
        """

        entries = extract_share_entries(text)

        self.assertEqual(entries[0].label, "设计文档集合")
        self.assertEqual(entries[1].label, "项目资料归档")


if __name__ == "__main__":
    unittest.main()
