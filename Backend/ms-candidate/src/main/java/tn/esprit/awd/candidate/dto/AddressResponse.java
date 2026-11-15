package tn.esprit.awd.candidate.dto;

public record AddressResponse(
        Long id,
        String street,
        String houseNumber,
        String zipCode,
        Long candidateId
) {
}
