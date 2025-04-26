from src.services.text_parser import TextParser

def test_text_parser():
    parser = TextParser()
    job_description = (
        "A career in IBM Software means joining a team that transforms customer challenges into innovative solutions. "
        "As a back-end developer, you will design and implement cutting-edge features, optimize existing code, and ensure "
        "high-quality software through rigorous testing and debugging. Collaborating with developers, designers, and product "
        "managers, you will help create AI-powered, cloud-native solutions that meet user needs."
    )
    metadata = parser.parse_text(job_description, parse_type="job")
    print(metadata)