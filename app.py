import os
from flask import Flask, request
from github import Github, GithubIntegration

app = Flask(__name__)

app_id = '174823'

# Read the bot certificate
with open(
        os.path.normpath(os.path.expanduser('key.pem')),
        'r'
) as cert_file:
    app_key = cert_file.read()

# Create an GitHub integration instance
git_integration = GithubIntegration(
    app_id,
    app_key,
)


# Example
def pr_opened_event(repo, payload):
    pr = repo.get_issue(number=payload['pull_request']['number'])
    author = pr.user.login

    is_first_pr = repo.get_issues(creator=author).totalCount

    if is_first_pr == 1:
        response = f"Thanks for opening this pull request, @{author}! " \
                   f"The repository maintainers will look into it ASAP! :speech_balloon:"
        pr.create_comment(f"{response}")
        pr.add_to_labels("needs review")


# Question 1
def pr_closed_event(repo, payload):
    pr = repo.get_issue(number=payload['pull_request']['number'])
    author = pr.user.login
    response = f"Thank you for your contribution, {author} \n Your pull request is now closed"
    pr.create_comment(f"{response}")


# Question 2
def pr_merged_and_delete(repo, payload):
    pr = repo.get_issue(number=payload['pull_request']['number'])
    ref = f'heads/{payload["pull_request"]["head"]["ref"]}'
    pr.create_comment(f'Delete branch {ref}')
    repo.get_git_ref(ref).delete()


# Question 3
# Part 1
def pr_work_in_progress_detected(repo, sha, pr):
    repo.get_commit(sha=sha).create_status(
        state='pending',
        context='umons-bot-tutorial/WIP'
    )
    pr.create_comment(f'Your commit {sha} is pending')


# Part 2
def pr_work_in_progress_end(repo, sha, pr):
    if not any(label.name == 'pending' for label in pr.labels):
        repo.get_commit(sha=sha).create_status(
            state='successful',
            context='umons-bot-tutorial/WIP'
        )
        pr.create_comment(f'Success for {sha}')


@app.route("/", methods=['POST'])
def bot():
    payload = request.json

    if not 'repository' in payload.keys():
        return "", 204

    owner = payload['repository']['owner']['login']
    repo_name = payload['repository']['name']

    git_connection = Github(
        login_or_token=git_integration.get_access_token(
            git_integration.get_installation(owner, repo_name).id
        ).token
    )
    repo = git_connection.get_repo(f"{owner}/{repo_name}")

    # Check if the event is a GitHub pull request creation event
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'opened':
        pr_opened_event(repo, payload)
    # Question 1
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'closed':
        pr_closed_event(repo, payload)

    # Question 2
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['pull_request']['merged']:
        pr_merged_and_delete(repo, payload)

    # Question 3
    title = payload['pull_request']['title']
    pr = repo.get_issue(number=payload['pull_request']['number'])
    ref = f'heads/{payload["pull_request"]["head"]["ref"]}'
    sha = repo.get_git_ref(ref).object.sha  # ERROR Here "Not Found"

    # Part 1
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'opened':
        if title.find("WIP") != -1 or title.find("work in progress") != -1 or title.find("do not merge") != -1:
            pr_work_in_progress_detected(repo, sha, pr)

    # Part 2
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'edited':
        if title.find("WIP") != -1 or title.find("work in progress") != -1 or title.find("do not merge") != -1:
            pr_work_in_progress_detected(repo, sha, pr)

        else:
            pr_work_in_progress_end(repo, sha, pr)

    return "", 204


if __name__ == "__main__":
    app.run(debug=True, port=5000)
