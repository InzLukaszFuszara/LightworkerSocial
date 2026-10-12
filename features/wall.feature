Feature: User profile wall with tiles
  As a visitor
  I want to see a user's wall as a grid of tiles
  So that I can quickly browse their posts

  Background:
    Given a category "Healing" exists
    And a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"

  Scenario: The wall shows the profile and the posts as tiles, newest first
    Given "anna" has posted "First post" in category "Healing"
    And "anna" has posted "Second post" in category "Healing"
    When I visit the wall of "anna"
    Then the page should contain "anna"
    And I should see 2 tiles
    And the tiles should be laid out 3 per row
    And tile 1 should contain "Second post"
    And tile 2 should contain "First post"

  Scenario: A tile shows only the first 250 characters
    Given "anna" has posted a text of 600 characters in category "Healing"
    When I visit the wall of "anna"
    Then tile 1 should show an excerpt of 250 characters
    And the lightbox content of tile 1 should contain the full text

  Scenario: A tile shows the first image as a thumbnail
    Given "anna" has posted "With pictures" with 2 images in category "Healing"
    When I visit the wall of "anna"
    Then tile 1 should show the thumbnail of the first image

  Scenario: A tile links to the category of the post
    Given "anna" has posted "Categorised" in category "Healing"
    When I visit the wall of "anna"
    Then tile 1 should link to the forum topic "Healing"

  Scenario: A tile opens the full post in a lightbox
    Given "anna" has posted "Full **markdown** content #peace" in category "Healing"
    When I visit the wall of "anna"
    Then tile 1 should be a lightbox trigger
    And the lightbox content of tile 1 should contain "<strong>markdown</strong>"

  Scenario: The wall only shows posts of its owner
    Given a user "bob" with e-mail "bob@example.com" and password "S3cret-pass!"
    And "anna" has posted "Anna's thoughts" in category "Healing"
    And "bob" has posted "Bob's thoughts" in category "Healing"
    When I visit the wall of "anna"
    Then I should see 1 tile
    And the page should not contain "Bob&#x27;s thoughts"

  Scenario: The owner sees a button to add a post
    Given I am logged in as "anna"
    When I visit the wall of "anna"
    Then the page should contain a link to the new post page

  Scenario: The list of profiles links to the walls
    Given a user "bob" with e-mail "bob@example.com" and password "S3cret-pass!"
    When I visit the profile list
    Then the page should link to the wall of "anna"
    And the page should link to the wall of "bob"
