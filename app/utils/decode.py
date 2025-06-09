import codecs

def decode_unicode_escape(text):
    if isinstance(text, str) and '\\u' in text:
        try:
            return codecs.decode(text, 'unicode_escape')
        except UnicodeDecodeError:
            return text
    return text