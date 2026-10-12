Feature: Comments on posts
  As a user
  I want to comment on posts
  And read the discussion on the forum

  Background:
    Given a category "Meditation" exists
    And a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    And a user "bob" with e-mail "bob@example.com" and password "S3cret-pass!"
    And a user "carol" with e-mail "carol@example.com" and password "S3cret-pass!"
    And "anna" has posted "Morning light" in category "Meditation"

  Scenario: Adding a comment
    Given I am logged in as "bob"
    When I comment "Beautiful words" on the latest post
    Then the latest post should have the comments "Beautiful words"
    And I should be redirected to the comment "Beautiful words"

  Scenario: The number of comments is shown under the tiles
    Given "bob" has commented "One" on the latest post
    And "carol" has commented "Two" on the latest post
    When I visit the wall of "anna"
    Then tile 1 should show 2 comments

  Scenario: The forum shows each post in its own row with its comments below
    Given "anna" has posted "Evening calm" in category "Meditation"
    And "bob" has commented "First!" on the post "Morning light"
    And "carol" has commented "Lovely" on the post "Morning light"
    And "bob" has commented "So calm" on the post "Evening calm"
    And I am logged in as "carol"
    When I visit the forum topic "Meditation"
    Then I should see 2 forum posts
    And forum post 1 should contain "Evening calm"
    And forum post 1 should list the comments "So calm"
    And forum post 2 should contain "Morning light"
    And forum post 2 should list the comments "First!, Lovely"
    And every forum post should take a whole row
    And every forum post should have a comment form

  Scenario: Commenting from the forum returns to the forum
    Given I am logged in as "bob"
    When I comment "Nice" on the latest post from the forum topic "Meditation"
    Then I should be redirected to the forum topic "Meditation"

  Scenario: The post page shows the comments
    Given "bob" has commented "Beautiful" on the latest post
    When I open the latest post
    Then the page should contain "Beautiful"

  Scenario: Comments are plain text
    Given I am logged in as "bob"
    When I comment "<script>alert(1)</script> **not bold**" on the latest post
    And I open the latest post
    Then the page should not contain "<script>alert(1)"
    And the page should contain "**not bold**"

  Scenario: An empty comment is rejected
    Given I am logged in as "bob"
    When I comment "" on the latest post
    Then the latest post should have 0 comments

  Scenario: A comment can have at most 1000 characters
    Given I am logged in as "bob"
    When I comment with 1001 characters on the latest post
    Then the latest post should have 0 comments
    When I comment with 1000 characters on the latest post
    Then the latest post should have 1 comment

  Scenario: Anonymous visitors cannot comment
    When an anonymous visitor comments "Spam" on the latest post
    Then the latest post should have 0 comments
    When I visit the forum topic "Meditation"
    Then the page should contain "Zaloguj się, aby komentować"

  Scenario Outline: Deleting comments
    Given "bob" has commented "Hello" on the latest post
    And I am logged in as "<user>"
    When I delete the comment "Hello"
    Then the response status should be <status>
    And the latest post should have <count> comments

    Examples: the author of the comment and of the post may delete it
      | user  | status | count |
      | bob   | 302    | 0     |
      | anna  | 302    | 0     |
      | carol | 403    | 1     |
