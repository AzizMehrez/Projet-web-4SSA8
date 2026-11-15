package tn.esprit.awd.candidate.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CandidateRequest(

        @NotBlank(message = "firstname is required")
        @Size(max = 50)
        String firstname,

        @NotBlank(message = "lastname is required")
        @Size(max = 50)
        String lastname,

        @NotBlank(message = "email is required")
        @Email(message = "email must be a valid email address")
        String email,

        @Valid
        AddressRequest address
) {
}
