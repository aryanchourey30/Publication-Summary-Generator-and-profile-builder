import pandas as pd
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from transformers import pipeline
import re


# Load Summarization Model
summarizer = pipeline("summarization", model="t5-small")

# Load the dataset
new_data = '/content/sample_data/minor data of faculty new 2.xlsx'  # Update with your dataset's path
df = pd.read_excel(new_data)

# Clean column names to avoid KeyErrors due to formatting issues
df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace(' ', '_').str.lower()

def extract_from_pdf(url):
    """
    Download and extract text from a PDF file.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Save the PDF to a temporary file
        with open("temp.pdf", "wb") as file:
            file.write(response.content)

        # Read the PDF content
        reader = PdfReader("temp.pdf")
        text = ""
        for page in reader.pages:
            text += page.extract_text()

        return text[:1000]  # Return the first 500 characters as a sample
    except Exception as e:
        return f"Error processing PDF: {e}"

def extract_abstract(url):
    """
    Fetch and extract the abstract from the given URL.
    """
    if url.endswith('.pdf'):
        return extract_from_pdf(url)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        abstract_meta = soup.find('meta', attrs={'name': 'twitter:description'})
        if abstract_meta and 'content' in abstract_meta.attrs:
            return abstract_meta['content']
        return "Abstract not found in the meta tag!"
    except requests.exceptions.RequestException as e:
        return f"Error while fetching the URL: {e}"

def generate_summary(abstract):
    """
    Generate a summary of the abstract using an LLM.
    """
    if abstract.startswith("Error"):
        return "Cannot summarize the abstract due to an error in fetching."
    summary = summarizer(abstract, max_length=500, min_length=50, do_sample=False)
    return summary[0]['summary_text']

def extract_expertise(abstract):
    """
    Dynamically extract expertise fields from the abstract text.
    """
    expertise_keywords = [
        'AI', 'machine learning', 'data science', 'biology',
        'physics', 'chemistry', 'robotics', 'neuroscience', 'engineering',
        'quantum computing', 'genomics', 'renewable energy', 'cybersecurity',
        'nanotechnology', 'climate science', 'blockchain', 'mathematics', 'statistics'
    ]
    expertise_found = [keyword for keyword in expertise_keywords if keyword.lower() in abstract.lower()]
    return ", ".join(expertise_found) if expertise_found else "General"

def build_profile(abstract, author_name=None, doi=None, department=None, title=None):
    """
    Build a profile dynamically by analyzing the abstract text and optional URL.
    """
    profile = {}

    # Extract the Title of the Paper
    profile["Title of the Paper"] = title if title else "Unknown"

    # Extract Expertise
    profile["Expertise"] = extract_expertise(abstract)

    # Add Additional Details
    profile["Name of Author"] = author_name if author_name else "Unknown"
    profile["DOI"] = doi if doi else "Unknown"
    profile["Department"] = department if department else "Unknown"

    return profile

def search_by_author(data):
    """
    Search for an author and display further options to filter and get details.
    """
    author = input("Enter the author's name to search: ").strip()
    author_data = data[data['name_of_the_author'].str.contains(author, case=False, na=False)]

    if author_data.empty:
        print(f"No results found for author: {author}")
        return

    print("\nDepartments associated with the author:")
    departments = author_data['department_of_the_teacher'].unique()
    for i, dept in enumerate(departments, 1):
        print(f"{i}. {dept}")

    dept_choice = input("\nEnter the number corresponding to the department: ").strip()
    if dept_choice.isdigit() and 1 <= int(dept_choice) <= len(departments):
        selected_dept = departments[int(dept_choice) - 1]
        filtered_data = author_data[author_data['department_of_the_teacher'] == selected_dept]

        print("\nPapers available:")
        for i, row in enumerate(filtered_data.itertuples(), 1):
            print(f"{i}. {row.title_of_paper} (Link: {row.link_of_the_article})")

        paper_choice = input("\nEnter the number corresponding to the paper you want the abstract for: ").strip()
        if paper_choice.isdigit() and 1 <= int(paper_choice) <= len(filtered_data):
            selected_paper = filtered_data.iloc[int(paper_choice) - 1]
            print(f"\nFetching abstract for: {selected_paper['title_of_paper']}")

            abstract = extract_abstract(selected_paper['link_of_the_article'])
            print(f"\nAbstract:\n{abstract}")

            # Generate summary
            summary = generate_summary(abstract)
            print(f"\nSummary:\n{summary}")

            # Build profile
            profile = build_profile(
                abstract,
                author_name=selected_paper['name_of_the_author'],
                doi=selected_paper['link_of_the_article'],
                department=selected_paper['department_of_the_teacher'],
                title=selected_paper['title_of_paper']
            )
            print("\nProfile:")
            for key, value in profile.items():
                print(f"{key}: {value}")
        else:
            print("Invalid choice. Exiting.")
    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    search_by_author(df)
