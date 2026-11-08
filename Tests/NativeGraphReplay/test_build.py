"""Synthetic cache-boundary tests; no original binary or golden reads."""
import unittest

from build import validate_extra_flags


class ExtraCompilerFlagsTest(unittest.TestCase):
    def test_empty_environment_is_supported(self):
        for value in ('', ' ', '\t\n'):
            with self.subTest(value=value):
                self.assertIsNone(validate_extra_flags(value))

    def test_all_extra_arguments_are_rejected(self):
        # There is intentionally no parser or allowlist to bypass: even benign
        # extras are unsupported by this bounded builder.
        probes = (
            '-Wp,-include,/absolute/header',
            '-Wp,-include,/absolute/header -O2',
            '--config=/absolute/config', '--config /absolute/config',
            '-include /absolute/header', '-I/absolute/include',
            '-DVALUE=1', '-DVALUE=/absolute/header',
            '-fplugin=/absolute/plugin', '-Xclang -load -Xclang /absolute/plugin',
            '@/absolute/response', '-Wl,@/absolute/response',
            '-L/absolute/library -lcustom',
            '-O2', '-g', '-Wall', '""', "''", '\n--config=config\t',
        )
        for value in probes:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'CLAW_NATIVE_CXXFLAGS is unsupported'):
                    validate_extra_flags(value)


if __name__ == '__main__':
    unittest.main()
