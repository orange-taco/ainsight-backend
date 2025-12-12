from datetime import datetime

def map_submission(submission) -> dict:
    return {
        "source": "reddit",
        "post_id": submission.id,
        "subreddit": submission.subreddit.display_name,
        "title": submission.title,
        "author": str(submission.author),
        "created_at": datetime.utcfromtimestamp(submission.created_utc),
        "score": submission.score,
        "num_comments": submission.num_comments,
        "url": submission.url,
        "raw": {
            "selftext": submission.selftext
        }
    }
