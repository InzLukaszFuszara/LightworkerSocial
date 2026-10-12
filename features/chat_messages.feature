Feature: Direct conversations
  As a user
  I want to exchange short messages and images with another user

  Background:
    Given a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    And a user "bob" with e-mail "bob@example.com" and password "S3cret-pass!"
    And a user "eve" with e-mail "eve@example.com" and password "S3cret-pass!"

  Scenario: Sending a message to another user
    When "anna" starts a conversation with "bob"
    And "anna" sends the message "Hi Bob!"
    Then "bob" should have 1 unread message
    And "bob" should see the message "Hi Bob!" from "anna"

  Scenario: Reading the conversation marks it as read
    Given "anna" starts a conversation with "bob"
    And "anna" sends the message "Hi Bob!"
    When "bob" reads the conversation
    Then "bob" should have 0 unread messages

  Scenario: Starting a conversation twice reuses it
    When "anna" starts a conversation with "bob"
    And "bob" starts a conversation with "anna"
    Then there should be 1 conversation between "anna" and "bob"

  Scenario: A message can have at most 250 characters
    Given "anna" starts a conversation with "bob"
    When "anna" sends a message of 251 characters
    Then the message should be rejected
    When "anna" sends a message of 250 characters
    Then the message should be accepted

  Scenario: Markdown is not interpreted in chat messages
    Given "anna" starts a conversation with "bob"
    When "anna" sends the message "**not bold** <b>tag</b>"
    Then "bob" should see the message "**not bold** <b>tag</b>" from "anna"

  Scenario: An empty message is rejected
    Given "anna" starts a conversation with "bob"
    When "anna" sends the message ""
    Then the message should be rejected

  Scenario Outline: Images are converted to WebP
    Given "anna" starts a conversation with "bob"
    When "anna" sends a <format> image "picture.<ext>"
    Then the message should be accepted
    And the image of the last message should be stored as WebP
    And "bob" should be able to download the image of the last message

    Examples:
      | format | ext  |
      | JPEG   | jpg  |
      | PNG    | png  |
      | GIF    | gif  |
      | WEBP   | webp |

  Scenario: Images larger than 5 MiB are rejected
    Given "anna" starts a conversation with "bob"
    When "anna" sends an image larger than 5 MiB
    Then the message should be rejected

  Scenario: Unsupported image formats are rejected
    Given "anna" starts a conversation with "bob"
    When "anna" sends a BMP image "old.bmp"
    Then the message should be rejected

  Scenario: Outsiders cannot read a conversation or its images
    Given "anna" starts a conversation with "bob"
    And "anna" sends a PNG image "private.png"
    When "eve" opens the conversation
    Then the response status should be 404
    And "eve" should not be able to download the image of the last message

  Scenario: Nobody can start a conversation with themselves
    When "anna" starts a conversation with "anna"
    Then the response status should be 400
