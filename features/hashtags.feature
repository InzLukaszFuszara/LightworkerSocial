Feature: Hashtags
  As a visitor
  I want to click a hashtag
  So that I can see every post with that hashtag

  Background:
    Given a category "Meditation" exists
    And a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    And a user "bob" with e-mail "bob@example.com" and password "S3cret-pass!"

  Scenario: Hashtags in a post are links
    Given "anna" has posted "Morning practice #Light and #spokój" in category "Meditation"
    When I open the latest post
    Then the page should link to the hashtag "light"
    And the page should link to the hashtag "spokój"

  Scenario: The hashtag page lists posts of all users sorted by date
    Given "anna" has posted "Old #light post" in category "Meditation" 3 days ago
    And "bob" has posted "Newest #light post" in category "Meditation" 1 day ago
    And "anna" has posted "Middle #LIGHT post" in category "Meditation" 2 days ago
    And "bob" has posted "Unrelated #dark post" in category "Meditation"
    When I visit the hashtag page "light"
    Then I should see 3 tiles
    And tile 1 should contain "Newest"
    And tile 2 should contain "Middle"
    And tile 3 should contain "Old"

  Scenario: Hashtags inside code are not tags
    Given "anna" has posted "Use `#notatag` in code but #real outside" in category "Meditation"
    Then the latest post should have the hashtags "real"
