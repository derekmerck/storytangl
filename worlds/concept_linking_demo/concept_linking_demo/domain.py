"""Adopt lexical linking independently from provider naming policy."""
from tangl.prose.linking import LinkedProseYamlCodec
from tangl.prose.naming import NamingActor, NamingLocation, ProseBlock, get_authorities


def get_story_codecs() -> dict[str, LinkedProseYamlCodec]:
    codec = LinkedProseYamlCodec()
    return {codec.codec_id: codec}
