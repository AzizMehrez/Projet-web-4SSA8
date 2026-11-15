package tn.esprit.awd.candidate.mapper;

import tn.esprit.awd.candidate.dto.AddressRequest;
import tn.esprit.awd.candidate.dto.AddressResponse;
import tn.esprit.awd.candidate.dto.CandidateRequest;
import tn.esprit.awd.candidate.dto.CandidateResponse;
import tn.esprit.awd.candidate.entity.Address;
import tn.esprit.awd.candidate.entity.Candidate;

public final class CandidateMapper {

    private CandidateMapper() {
    }

    public static Candidate toEntity(CandidateRequest request) {
        Candidate candidate = new Candidate(request.firstname(), request.lastname(), request.email());
        if (request.address() != null) {
            candidate.setAddress(toEntity(request.address()));
        }
        return candidate;
    }

    public static Address toEntity(AddressRequest request) {
        return new Address(request.street(), request.houseNumber(), request.zipCode());
    }

    public static void updateEntity(Address address, AddressRequest request) {
        address.setStreet(request.street());
        address.setHouseNumber(request.houseNumber());
        address.setZipCode(request.zipCode());
    }

    public static CandidateResponse toResponse(Candidate candidate) {
        return new CandidateResponse(
                candidate.getId(),
                candidate.getFirstname(),
                candidate.getLastname(),
                candidate.getEmail(),
                candidate.getAddress() == null ? null : toResponse(candidate.getAddress())
        );
    }

    public static AddressResponse toResponse(Address address) {
        Long candidateId = address.getCandidate() == null ? null : address.getCandidate().getId();
        return new AddressResponse(
                address.getId(),
                address.getStreet(),
                address.getHouseNumber(),
                address.getZipCode(),
                candidateId
        );
    }
}
