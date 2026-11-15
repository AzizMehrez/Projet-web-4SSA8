package tn.esprit.awd.candidate.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record AddressRequest(

        @NotBlank(message = "street is required")
        @Size(max = 150)
        String street,

        @NotBlank(message = "houseNumber is required")
        @Size(max = 10)
        String houseNumber,

        @NotBlank(message = "zipCode is required")
        @Pattern(regexp = "^[A-Za-z0-9 -]{3,10}$", message = "zipCode must be 3 to 10 letters, digits, spaces or dashes")
        String zipCode
) {
}
