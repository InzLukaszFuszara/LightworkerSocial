Feature: Markdown in posts
  As an author
  I want to format my posts with Markdown
  While the site stays safe from malicious markup

  Background:
    Given a category "Meditation" exists
    And a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"

  Scenario Outline: Markdown is rendered
    Given "anna" has posted "<source>" in category "Meditation"
    When I open the latest post
    Then the page should contain the markup <html>

    Examples:
      | source                         | html                                       |
      | **bold**                       | <strong>bold</strong>                      |
      | *italic*                       | <em>italic</em>                            |
      | # Heading                      | <h1>Heading</h1>                           |
      | [link](https://example.com)    | <a href="https://example.com" rel="nofollow">link</a> |
      | `code`                         | <code>code</code>                          |

  Scenario: Dangerous HTML is removed
    Given "anna" has posted "<script>alert(1)</script> <a href='javascript:alert(1)'>x</a>" in category "Meditation"
    When I open the latest post
    Then the page should not contain "<script>alert(1)"
    And the page should not contain "javascript:alert"

  Scenario: A hashtag at the start of a line is not a heading
    Given "anna" has posted "#gratitude every day" in category "Meditation"
    When I open the latest post
    Then the page should not contain "<h1>gratitude"
    And the page should link to the hashtag "gratitude"

  Scenario: The tile excerpt is plain text
    Given "anna" has posted "**Bold** and _italic_" in category "Meditation"
    When I visit the wall of "anna"
    Then tile 1 should show the excerpt "Bold and italic"
