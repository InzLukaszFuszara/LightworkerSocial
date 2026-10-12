Feature: Adding a post to my wall
  As a logged in user
  I want to add posts with images to my wall
  So that I can share my thoughts with the community

  Background:
    Given a category "Meditation" exists
    And a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"

  Scenario: Anonymous visitors are sent to the login page
    When I open the new post page
    Then I should be redirected to the login page

  Scenario: Publishing a text post
    Given I am logged in as "anna"
    When I publish a post "Hello **world** #light" in category "Meditation"
    Then I should be redirected to the wall of "anna"
    And the wall of "anna" should show 1 tile
    And the latest post should be in category "Meditation"

  Scenario: A post can have at most 2000 characters
    Given I am logged in as "anna"
    When I publish a post of 2001 characters in category "Meditation"
    Then the post should be rejected
    And the page should contain "2000"

  Scenario: A post of exactly 2000 characters is accepted
    Given I am logged in as "anna"
    When I publish a post of 2000 characters in category "Meditation"
    Then the wall of "anna" should show 1 tile

  Scenario: A post must belong to a category
    Given I am logged in as "anna"
    When I publish a post "No category" without a category
    Then the post should be rejected

  Scenario Outline: Images are converted to WebP
    Given I am logged in as "anna"
    And I attach a <format> image "photo.<ext>"
    When I publish a post "Look at this" in category "Meditation"
    Then the latest post should have 1 image
    And every image of the latest post should be stored as WebP
    And the first image of the latest post should have a WebP thumbnail

    Examples:
      | format | ext  |
      | JPEG   | jpg  |
      | PNG    | png  |
      | GIF    | gif  |
      | WEBP   | webp |

  Scenario: A post can contain many images
    Given I am logged in as "anna"
    And I attach a JPEG image "one.jpg"
    And I attach a PNG image "two.png"
    And I attach a GIF image "three.gif"
    When I publish a post "Gallery" in category "Meditation"
    Then the latest post should have 3 images
    And every image of the latest post should be stored as WebP

  Scenario: An animated GIF stays animated after conversion
    Given I am logged in as "anna"
    And I attach an animated GIF image "anim.gif"
    When I publish a post "Animation" in category "Meditation"
    Then the first image of the latest post should be an animated WebP

  Scenario: Images larger than 5 MiB are rejected
    Given I am logged in as "anna"
    And I attach a PNG image "huge.png" larger than 5 MiB
    When I publish a post "Too big" in category "Meditation"
    Then the post should be rejected
    And the page should contain "huge.png"

  Scenario: Unsupported image formats are rejected
    Given I am logged in as "anna"
    And I attach a BMP image "old.bmp"
    When I publish a post "Bitmap" in category "Meditation"
    Then the post should be rejected
    And the page should contain "nieobsługiwany format"

  Scenario: Files that are not images are rejected
    Given I am logged in as "anna"
    And I attach a text file "notes.jpg"
    When I publish a post "Fake" in category "Meditation"
    Then the post should be rejected

  Scenario: The author can delete their post
    Given I am logged in as "anna"
    And "anna" has posted "To be removed" in category "Meditation"
    When I delete the latest post
    Then the wall of "anna" should show 0 tiles

  Scenario: Nobody else can delete a post
    Given a user "bob" with e-mail "bob@example.com" and password "S3cret-pass!"
    And "anna" has posted "Mine" in category "Meditation"
    And I am logged in as "bob"
    When I delete the latest post
    Then the response status should be 403
