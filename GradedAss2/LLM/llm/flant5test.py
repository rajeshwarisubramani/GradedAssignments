
from transformers import T5Tokenizer, T5ForConditionalGeneration

tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-xl")
model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-xl")

input_text = "translate English to German: How old are you?"
input_ids = tokenizer(input_text, return_tensors="pt").input_ids

outputs = model.generate(input_ids)
print(tokenizer.decode(outputs[0]))


from transformers import pipeline

# Load the model using pipeline (handles tokenizer + model automatically)
translator = pipeline("text2text-generation", model="google/flan-t5-xl")

# Run translation
result = translator("translate English to German: How old are you?")

print(result[0]["generated_text"])