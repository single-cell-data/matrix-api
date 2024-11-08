import unittest

from somacore import _mixin, ephemeral


class TestItem(unittest.TestCase):
    def test_get(self):
        the_a = _mixin.item(str)

        class ItemHaver(ephemeral.Collection):
            a = the_a
            b = _mixin.item(int, "base_b")

        self.assertIs(the_a, ItemHaver.a)

        items = ItemHaver()
        items["c"] = "d"

        with self.assertRaises(AttributeError):
            items.a
        with self.assertRaises(AttributeError):
            items.b
        with self.assertRaises(AttributeError):
            del items.a

        self.assertEqual("d", items["c"])

        items["a"] = "a"
        items["base_b"] = 1
        self.assertEqual("a", items.a)
        self.assertEqual(1, items.b)

        items.a = "hello"
        items.b = 500

        self.assertEqual(dict(a="hello", base_b=500, c="d"), dict(items))
        del items.a
        self.assertEqual(dict(base_b=500, c="d"), dict(items))
