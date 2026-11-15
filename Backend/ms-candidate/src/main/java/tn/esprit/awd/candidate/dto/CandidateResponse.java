package tn.esprit.awd.candidate.dto;

public record CandidateResponse(
        Long id,
        String firstname,
        String lastname,
        String email,
        AddressResponse address
) {
}
