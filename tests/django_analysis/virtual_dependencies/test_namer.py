from extended_mypy_django_plugin.django_analysis import (
    ImportPath,
    adler32_hash,
    virtual_dependencies,
)


class TestVirtualDependencyNamer:
    def test_it_can_name_virtual_dependencies(self) -> None:
        namer = virtual_dependencies.VirtualDependencyNamer(
            namespace=ImportPath("some.where.nice"), hasher=adler32_hash
        )

        assert namer(ImportPath("my.nice.model")) == "some.where.nice.mod_577176819"
        assert namer(ImportPath("my.other.model")) == "some.where.nice.mod_685704566"

        def bad_hasher(*vals: bytes) -> str:
            return f"__hashed__{b'_'.join(vals).replace(b'.', b'DD').decode()}"

        namer = virtual_dependencies.VirtualDependencyNamer(
            namespace=ImportPath("a.bad.place"), hasher=bad_hasher
        )

        assert namer(ImportPath("my.nice.model")) == "a.bad.place.mod___hashed__myDDniceDDmodel"
        assert namer(ImportPath("my.other.model")) == "a.bad.place.mod___hashed__myDDotherDDmodel"
