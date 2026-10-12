Feature: Polish and English language versions
  As a visitor
  I want to use the site in Polish or English

  Background:
    Given a category "Medytacja" with English name "Meditation" exists

  Scenario: Polish is the default language
    When I visit the forum
    Then the page should contain "Ostatni wpis"
    And I should see the forum topic "Medytacja"

  Scenario: Switching to English
    When I switch the language to "en"
    And I visit the forum
    Then the page should contain "Last post"
    And I should see the forum topic "Meditation"

  Scenario: Switching back to Polish
    When I switch the language to "en"
    And I switch the language to "pl"
    And I visit the forum
    Then the page should contain "Ostatni wpis"

  Scenario Outline: Validation messages are translated
    Given a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    And I use the language "<lang>"
    When I log in with e-mail "anna@example.com" and password "bad"
    Then the page should contain "<message>"

    Examples:
      | lang | message                           |
      | pl   | Nieprawidłowy e-mail lub hasło.   |
      | en   | Invalid e-mail or password.       |
