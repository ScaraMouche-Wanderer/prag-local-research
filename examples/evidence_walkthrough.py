"""Run PRAG's exact-definition and missing-evidence paths on synthetic inputs."""

import os

from scripts.answer import format_excerpts_block, generate_answer, lookup_option_definition


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    source = os.path.join(BASE_DIR, "demo-corpus", "overview.md")
    with open(source, encoding="utf-8") as document:
        excerpt = {"file_name": os.path.basename(source), "chunk_text": document.read()}
    question = "What does --group-events do?"
    answer = lookup_option_definition(question, [excerpt])
    if answer is None:
        raise SystemExit("The sample document is missing the exact option definition.")

    print("PRAG evidence walkthrough | synthetic document, no model calls")
    print(f"\nQuestion: {question}")
    print(f"\nExcerpt:\n{format_excerpts_block([excerpt], question)}")
    print(f"Answer:\n{answer}")

    missing_question = "What is BeaconDesk's measured latency?"
    print(f"\nQuestion: {missing_question}")
    print("Retrieved excerpts: 0 (simulated retrieval miss)")
    print(f"\nAnswer:\n{generate_answer(missing_question, [], route='local_file')}")


if __name__ == "__main__":
    main()
