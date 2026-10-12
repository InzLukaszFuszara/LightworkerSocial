Feature: Liking posts and comments
  As a user
  I want to like posts and comments
  So that I can show what I appreciate

  Background:
    Given a category "Meditation" exists
    And a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    And a user "bob" with e-mail "bob@example.com" and password "S3cret-pass!"
    And a user "carol" with e-mail "carol@example.com" and password "S3cret-pass!"
    And "anna" has posted "Morning light" in category "Meditation"

  Scenario: Likes are shown under the tiles
    Given "bob" likes the latest post
    And "carol" likes the latest post
    When I visit the wall of "anna"
    Then tile 1 should show 2 likes

  Scenario: Liking a post
    Given I am logged in as "bob"
    When I like the latest post
    Then the latest post should have 1 like
    When I visit the wall of "anna"
    Then tile 1 should show 1 like
    And the like button of tile 1 should be pressed

  Scenario: Clicking like again removes the like
    Given I am logged in as "bob"
    When I like the latest post
    And I like the latest post
    Then the latest post should have 0 likes

  Scenario: A user can like a post only once
    Given "bob" likes the latest post
    When "bob" likes the latest post through the API
    Then the latest post should have 0 likes
    When "bob" likes the latest post through the API
    Then the API should answer that the post is liked with 1 like

  Scenario: Anonymous visitors are asked to log in
    When I visit the wall of "anna"
    Then the like button of tile 1 should link to the login page
    When an anonymous visitor likes the latest post
    Then the latest post should have 0 likes

  Scenario: Liking a comment
    Given "bob" has commented "Beautiful!" on the latest post
    And I am logged in as "carol"
    When I like the comment "Beautiful!"
    Then the comment "Beautiful!" should have 1 like
    When I visit the forum topic "Meditation"
    Then the comment "Beautiful!" should show 1 like

  Scenario: Unliking a comment
    Given "bob" has commented "Beautiful!" on the latest post
    And I am logged in as "carol"
    When I like the comment "Beautiful!"
    And I like the comment "Beautiful!"
    Then the comment "Beautiful!" should have 0 likes

  @browser
  Scenario: Liking in the browser updates the counter without reloading
    When "bob" opens the wall of "anna" in the browser
    And I click the like button of tile 1 in the browser
    Then the like button of tile 1 in the browser should show 1 and be pressed
    And the latest post should have 1 like
    And the page should not have been reloaded
    And there should be no JavaScript errors
