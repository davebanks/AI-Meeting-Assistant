from transformers import AutoTokenizer, AutoModelForCausalLM


print("Loading Qwen model...")

model_name = "Qwen/Qwen2.5-0.5B-Instruct"


tokenizer = AutoTokenizer.from_pretrained(
    model_name
)


model = AutoModelForCausalLM.from_pretrained(
    model_name
)


print("Qwen model loaded successfully.")


messages = [
    {
        "role": "system",
        "content": (
            "You are a meeting assistant. "
            "Summarize meetings clearly and accurately."
        )
    },
    {
        "role": "user",
        "content": (
            "Summarize this meeting transcript:\n\n"
            "We discussed creating a new website. "
            "John will prepare the homepage design by Friday. "
            "Mary will review the design next Monday. "
            "The team agreed to launch the website next month."
        )
    }
]


text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)


model_inputs = tokenizer(
    [text],
    return_tensors="pt"
)


print("Generating response...")


generated_ids = model.generate(
    **model_inputs,
    max_new_tokens=300
)


generated_ids = [
    output_ids[len(input_ids):]
    for input_ids, output_ids
    in zip(
        model_inputs.input_ids,
        generated_ids
    )
]


response = tokenizer.batch_decode(
    generated_ids,
    skip_special_tokens=True
)[0]


print("\n========== QWEN RESPONSE ==========\n")

print(response)

print("\n====================================")