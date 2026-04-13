from transformers import AutoTokenizer, AutoModel
name = 'sentence-transformers/all-MiniLM-L6-v2'
tok = AutoTokenizer.from_pretrained(name)
mod = AutoModel.from_pretrained(name)
tok.save_pretrained('./local_model')
mod.save_pretrained('./local_model')
print('local_model cached')

